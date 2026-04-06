"""
Rank Tracker Agent — daily SERP position checking.
Loads active projects → queries DataForSEO → saves rank_history → flags anomalies.
"""
import asyncio
import json
import time
from datetime import date, datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
import structlog

from app.core.database import get_sync_db
from app.models.project import Project
from app.models.keyword import Keyword, RankHistory
from app.models.competitor import Competitor
from app.models.agent_run import AgentRun, AgentType, RunStatus
from app.services.dataforseo import dataforseo_service, DataForSEOService

logger = structlog.get_logger()

# Anomaly threshold: flag if position changed by more than this
ANOMALY_THRESHOLD = 5


def run(project_id: str | None = None):
    """
    Main entry point. Runs for all active projects, or a specific one.
    Called from Celery task (sync context).
    """
    started = time.time()

    with get_sync_db() as db:
        # Load projects
        query = (
            select(Project)
            .where(Project.is_active == True)
            .options(
                joinedload(Project.keywords),
                joinedload(Project.competitors),
            )
        )
        if project_id:
            query = query.where(Project.id == project_id)

        projects = db.execute(query).unique().scalars().all()

        total_processed = 0
        total_failed = 0

        for project in projects:
            try:
                processed, failed = _process_project(db, project)
                total_processed += processed
                total_failed += failed
            except Exception as e:
                logger.error("Rank tracker failed for project",
                             project_id=project.id, error=str(e))
                total_failed += 1

        # Log agent run
        duration = time.time() - started
        run_log = AgentRun(
            project_id=project_id or "all",
            agent_type="rank_tracker",
            status="completed" if total_failed == 0 else "failed",
            items_processed=total_processed,
            items_failed=total_failed,
            duration_seconds=round(duration, 2),
            result_summary=json.dumps({
                "projects": len(projects),
                "keywords_checked": total_processed,
                "failed": total_failed,
            }),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_log)

    logger.info("🎯 Rank Tracker completed",
                projects=len(projects) if 'projects' in dir() else 0,
                processed=total_processed,
                failed=total_failed,
                duration=f"{duration:.1f}s")


def _process_project(db, project: Project) -> tuple[int, int]:
    """Process a single project: check ranks for all keywords."""
    today = date.today()

    active_keywords = [kw for kw in project.keywords if kw.is_active]
    if not active_keywords:
        return 0, 0

    # Collect all domains to track: project domain + competitor domains
    target_domains = [project.domain]
    for comp in project.competitors:
        if comp.is_active:
            target_domains.append(comp.domain)

    keyword_texts = [kw.keyword for kw in active_keywords]
    location_code = DataForSEOService.get_location_code(project.target_country)

    # Determine which devices to check
    devices = []
    if project.track_desktop:
        devices.append("desktop")
    if project.track_mobile:
        devices.append("mobile")
    if not devices:
        devices = ["desktop"]

    processed = 0
    failed = 0

    for device in devices:
        try:
            # Use live mode for immediate results
            # (batch mode requires polling, better for large volumes)
            results = asyncio.run(
                _check_all_keywords(
                    keyword_texts, target_domains,
                    location_code, project.target_language, device,
                )
            )

            # Build lookup: keyword_text → Keyword model
            kw_lookup = {kw.keyword.lower(): kw for kw in active_keywords}

            # Save results
            for result in results:
                kw_text = result["keyword"].lower()
                kw_model = kw_lookup.get(kw_text)
                if not kw_model:
                    continue

                # Get previous position for delta calculation
                prev = db.execute(
                    select(RankHistory)
                    .where(and_(
                        RankHistory.keyword_id == kw_model.id,
                        RankHistory.domain == result["domain"],
                        RankHistory.device == device,
                        RankHistory.checked_date < today,
                    ))
                    .order_by(RankHistory.checked_date.desc())
                    .limit(1)
                ).scalar_one_or_none()

                prev_position = prev.position if prev else None
                position = result.get("position")
                position_change = None
                if position is not None and prev_position is not None:
                    position_change = prev_position - position  # positive = improved

                # Check if already exists for today
                existing = db.execute(
                    select(RankHistory)
                    .where(and_(
                        RankHistory.keyword_id == kw_model.id,
                        RankHistory.domain == result["domain"],
                        RankHistory.device == device,
                        RankHistory.checked_date == today,
                    ))
                ).scalar_one_or_none()

                if existing:
                    existing.position = position
                    existing.url = result.get("url")
                    existing.position_change = position_change
                    existing.serp_features = json.dumps(result.get("serp_features", []))
                else:
                    rank_entry = RankHistory(
                        keyword_id=kw_model.id,
                        domain=result["domain"],
                        position=position,
                        url=result.get("url"),
                        device=device,
                        position_change=position_change,
                        serp_features=json.dumps(result.get("serp_features", [])),
                        checked_date=today,
                    )
                    db.add(rank_entry)

                processed += 1

                # Update keyword.latest_position for the project's own domain
                result_domain_clean = result["domain"].lower().removeprefix("www.")
                project_domain_clean = project.domain.lower().removeprefix("www.")
                if result_domain_clean == project_domain_clean and device == "desktop":
                    kw_model.latest_position = position
                    kw_model.position_change = position_change

            # Also record "not found" for domains not in results
            found_pairs = {(r["keyword"].lower(), r["domain"]) for r in results}
            for kw in active_keywords:
                for domain in target_domains:
                    if (kw.keyword.lower(), domain) not in found_pairs:
                        existing = db.execute(
                            select(RankHistory)
                            .where(and_(
                                RankHistory.keyword_id == kw.id,
                                RankHistory.domain == domain,
                                RankHistory.device == device,
                                RankHistory.checked_date == today,
                            ))
                        ).scalar_one_or_none()

                        if not existing:
                            rank_entry = RankHistory(
                                keyword_id=kw.id,
                                domain=domain,
                                position=None,  # not in top 100
                                device=device,
                                checked_date=today,
                            )
                            db.add(rank_entry)

        except Exception as e:
            logger.error("Device check failed", device=device,
                         project=project.domain, error=str(e))
            failed += 1

    return processed, failed


async def _check_all_keywords(
    keywords: list[str],
    target_domains: list[str],
    location_code: int,
    language_code: str,
    device: str,
) -> list[dict]:
    """Check all keywords via DataForSEO live mode."""
    all_results = []
    for kw in keywords:
        try:
            results = await dataforseo_service.check_ranks_live(
                keyword=kw,
                target_domains=target_domains,
                location_code=location_code,
                language_code=language_code,
                device=device,
            )
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"DataForSEO failed for '{kw}'", error=str(e))
    return all_results
