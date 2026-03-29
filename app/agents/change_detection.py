"""
Change Detection Agent — crawls competitor pages, detects changes.
Loads tracked pages → crawls with Playwright → diffs vs last snapshot → saves changes.
"""
import asyncio
import json
import time
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
import structlog

from app.core.database import get_sync_db
from app.models.project import Project
from app.models.competitor import Competitor
from app.models.page import TrackedPage, PageSnapshot, ChangeLog, ChangeSeverity
from app.models.agent_run import AgentRun, AgentType, RunStatus
from app.services.change_detection import change_detection_service

logger = structlog.get_logger()


def run(project_id: str | None = None):
    """Main entry point for Change Detection Agent."""
    started = time.time()

    with get_sync_db() as db:
        # Load all active tracked pages across projects
        query = (
            select(TrackedPage)
            .where(TrackedPage.is_active == True)
            .join(Competitor)
            .where(Competitor.is_active == True)
            .join(Project)
            .where(Project.is_active == True)
        )
        if project_id:
            query = query.where(Project.id == project_id)

        tracked_pages = db.execute(query).scalars().all()

        total_processed = 0
        total_changes = 0
        total_failed = 0

        for page in tracked_pages:
            try:
                changes_count = _process_page(db, page)
                total_processed += 1
                total_changes += changes_count
            except Exception as e:
                logger.error("Change detection failed for page",
                             url=page.url, error=str(e))
                total_failed += 1

        duration = time.time() - started
        run_log = AgentRun(
            project_id=project_id or "all",
            agent_type=AgentType.CHANGE_DETECTION,
            status=RunStatus.COMPLETED,
            items_processed=total_processed,
            items_failed=total_failed,
            duration_seconds=round(duration, 2),
            result_summary=json.dumps({
                "pages_crawled": total_processed,
                "changes_detected": total_changes,
                "failed": total_failed,
            }),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_log)

    logger.info("🕵️ Change Detection completed",
                pages=total_processed, changes=total_changes,
                failed=total_failed, duration=f"{duration:.1f}s")


def _process_page(db, page: TrackedPage) -> int:
    """Crawl a single page, compare with previous snapshot, save changes."""

    # 1. Crawl the page
    crawl_data = asyncio.run(change_detection_service.crawl_page(page.url))

    if "error" in crawl_data:
        logger.warning("Crawl returned error", url=page.url, error=crawl_data["error"])
        return 0

    # 2. Save new snapshot
    new_snapshot = PageSnapshot(
        tracked_page_id=page.id,
        title=crawl_data.get("title"),
        meta_description=crawl_data.get("meta_description"),
        h1=crawl_data.get("h1"),
        headings_json=crawl_data.get("headings_json"),
        word_count=crawl_data.get("word_count"),
        internal_links_count=crawl_data.get("internal_links_count"),
        external_links_count=crawl_data.get("external_links_count"),
        schema_markup=crawl_data.get("schema_markup"),
        content_hash=crawl_data.get("content_hash"),
        raw_text=crawl_data.get("raw_text"),
    )
    db.add(new_snapshot)
    db.flush()  # get new_snapshot.id

    # 3. Get previous snapshot
    prev_snapshot = db.execute(
        select(PageSnapshot)
        .where(and_(
            PageSnapshot.tracked_page_id == page.id,
            PageSnapshot.id != new_snapshot.id,
        ))
        .order_by(PageSnapshot.captured_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not prev_snapshot:
        logger.info("First snapshot for page, no diff", url=page.url)
        return 0

    # 4. Quick check: if content_hash hasn't changed, skip diff
    if prev_snapshot.content_hash == new_snapshot.content_hash:
        # Check meta fields too
        if (prev_snapshot.title == new_snapshot.title
                and prev_snapshot.meta_description == new_snapshot.meta_description
                and prev_snapshot.h1 == new_snapshot.h1):
            return 0

    # 5. Compare snapshots
    old_data = _snapshot_to_dict(prev_snapshot)
    new_data = _snapshot_to_dict(new_snapshot)
    changes = change_detection_service.compare_snapshots(old_data, new_data)

    if not changes:
        return 0

    # 6. Save change log entries
    for change in changes:
        severity_enum = ChangeSeverity(change["severity"])
        change_entry = ChangeLog(
            tracked_page_id=page.id,
            snapshot_before_id=prev_snapshot.id,
            snapshot_after_id=new_snapshot.id,
            severity=severity_enum,
            change_type=change["change_type"],
            field_name=change["field_name"],
            old_value=change.get("old_value"),
            new_value=change.get("new_value"),
            diff_html=change.get("diff_html"),
        )
        db.add(change_entry)

    overall = change_detection_service.classify_overall_severity(changes)
    logger.info("Changes detected", url=page.url,
                count=len(changes), severity=overall)

    return len(changes)


def _snapshot_to_dict(snapshot: PageSnapshot) -> dict:
    """Convert a PageSnapshot ORM model to a plain dict for comparison."""
    return {
        "title": snapshot.title,
        "meta_description": snapshot.meta_description,
        "h1": snapshot.h1,
        "headings_json": snapshot.headings_json,
        "word_count": snapshot.word_count,
        "internal_links_count": snapshot.internal_links_count,
        "external_links_count": snapshot.external_links_count,
        "schema_markup": snapshot.schema_markup,
        "content_hash": snapshot.content_hash,
        "raw_text": snapshot.raw_text,
    }
