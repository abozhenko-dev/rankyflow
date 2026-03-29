"""
GEO Visibility Agent — weekly AI visibility tracking.
Loads prompts → queries 5 LLM platforms → detects mentions → computes metrics.
"""
import asyncio
import json
import time
from datetime import date, datetime, timezone
from collections import defaultdict

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
import structlog

from app.core.database import get_sync_db
from app.models.user import User, PlanTier
from app.models.project import Project
from app.models.competitor import Competitor
from app.models.geo import (
    LLMPrompt, LLMResponse, LLMMention, GEOVisibilitySnapshot,
    LLMPlatform, Sentiment,
)
from app.models.agent_run import AgentRun, AgentType, RunStatus
from app.services.geo_visibility import geo_service

logger = structlog.get_logger()

# Platform access by plan tier
PLAN_PLATFORMS = {
    PlanTier.PRO: [LLMPlatform.CHATGPT, LLMPlatform.PERPLEXITY, LLMPlatform.GEMINI],
    PlanTier.AGENCY: list(LLMPlatform),  # all 5
}


def run(project_id: str | None = None):
    """Main entry point for GEO Visibility Agent."""
    started = time.time()

    with get_sync_db() as db:
        # Load projects with Pro/Agency plans that have prompts
        query = (
            select(Project)
            .where(Project.is_active == True)
            .join(User, Project.owner_id == User.id)
            .where(User.plan.in_([PlanTier.PRO, PlanTier.AGENCY]))
            .options(joinedload(Project.competitors))
        )
        if project_id:
            query = query.where(Project.id == project_id)

        projects = db.execute(query).unique().scalars().all()

        total_prompts = 0
        total_responses = 0
        total_failed = 0
        total_cost = 0.0

        for project in projects:
            try:
                # Get user's plan for platform access
                owner = db.execute(
                    select(User).where(User.id == project.owner_id)
                ).scalar_one()
                platforms = PLAN_PLATFORMS.get(owner.plan, [])
                if not platforms:
                    continue

                p_count, r_count, cost = _process_project(db, project, platforms)
                total_prompts += p_count
                total_responses += r_count
                total_cost += cost
            except Exception as e:
                logger.error("GEO failed for project",
                             project_id=project.id, error=str(e))
                total_failed += 1

        duration = time.time() - started
        run_log = AgentRun(
            project_id=project_id or "all",
            agent_type=AgentType.GEO_VISIBILITY,
            status=RunStatus.COMPLETED,
            items_processed=total_prompts,
            items_failed=total_failed,
            duration_seconds=round(duration, 2),
            api_cost_usd=round(total_cost, 4),
            result_summary=json.dumps({
                "projects": len(projects),
                "prompts_processed": total_prompts,
                "responses_collected": total_responses,
                "estimated_cost_usd": round(total_cost, 4),
            }),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_log)

    logger.info("👁️ GEO Visibility completed",
                prompts=total_prompts, responses=total_responses,
                cost=f"${total_cost:.3f}", duration=f"{duration:.1f}s")


def _process_project(
    db, project: Project, platforms: list[LLMPlatform]
) -> tuple[int, int, float]:
    """Process a single project's GEO visibility check."""
    today = date.today()

    # Load active prompts
    prompts = db.execute(
        select(LLMPrompt)
        .where(and_(
            LLMPrompt.project_id == project.id,
            LLMPrompt.is_active == True,
        ))
    ).scalars().all()

    if not prompts:
        return 0, 0, 0.0

    # Build competitor map
    competitor_names = {}
    for comp in project.competitors:
        if comp.is_active:
            competitor_names[comp.domain] = comp.name

    prompt_count = 0
    response_count = 0
    total_cost = 0.0

    # Per-platform aggregation for snapshot
    platform_mentions = defaultdict(list)  # platform → list of mention-lists

    for prompt in prompts:
        # Query all platforms
        results = asyncio.run(
            geo_service.query_all_platforms(prompt.prompt_text, platforms)
        )

        for result in results:
            if result.get("error"):
                continue

            platform = result["platform"]

            # Estimate cost
            tokens = result.get("tokens_used", 0)
            cost = _estimate_cost(platform, tokens)
            total_cost += cost

            # Save LLM response
            llm_response = LLMResponse(
                prompt_id=prompt.id,
                platform=platform,
                response_text=result["response_text"],
                cited_urls=json.dumps(result.get("cited_urls", [])),
                cited_domains=json.dumps(result.get("cited_domains", [])),
                source_count=len(result.get("cited_urls", [])),
                model_used=result.get("model_used"),
                tokens_used=tokens,
                api_cost_usd=round(cost, 6),
                checked_date=today,
            )
            db.add(llm_response)
            db.flush()

            # Detect brand mentions
            mentions = geo_service.detect_mentions(
                response_text=result["response_text"],
                brand_name=project.name,
                brand_domain=project.domain,
                competitor_names=competitor_names,
                cited_urls=result.get("cited_urls"),
            )

            # Save mentions
            for mention_data in mentions:
                mention = LLMMention(
                    response_id=llm_response.id,
                    domain=mention_data["domain"],
                    brand_name=mention_data["brand_name"],
                    is_mentioned=mention_data["is_mentioned"],
                    is_cited=mention_data["is_cited"],
                    is_recommended=mention_data["is_recommended"],
                    position_in_list=mention_data.get("position_in_list"),
                    mention_count=mention_data.get("mention_count", 0),
                    is_own_brand=mention_data["is_own_brand"],
                    sentiment_snippet=mention_data.get("sentiment_snippet"),
                    # sentiment will be filled by Analysis Agent later
                )
                db.add(mention)

            # Collect for aggregation
            platform_mentions[platform].append(mentions)
            response_count += 1

        prompt_count += 1

    # Compute and save aggregated snapshots per platform
    for platform, all_mentions in platform_mentions.items():
        metrics = geo_service.compute_visibility_metrics(all_mentions, project.domain)

        snapshot = GEOVisibilitySnapshot(
            project_id=project.id,
            platform=platform,
            total_prompts_checked=len(all_mentions),
            mention_rate=metrics["mention_rate"],
            citation_rate=metrics["citation_rate"],
            recommendation_rate=metrics["recommendation_rate"],
            avg_position=metrics["avg_position"],
            share_of_voice=metrics["share_of_voice"],
            snapshot_date=today,
        )
        db.add(snapshot)

    return prompt_count, response_count, total_cost


def _estimate_cost(platform: LLMPlatform, tokens: int) -> float:
    """Rough cost estimate per platform per request."""
    cost_per_1k_tokens = {
        LLMPlatform.CHATGPT: 0.00015 + 0.0006,   # gpt-4o-mini input+output
        LLMPlatform.PERPLEXITY: 0.001 + 0.001,    # sonar
        LLMPlatform.CLAUDE: 0.003 + 0.015,         # sonnet
        LLMPlatform.GEMINI: 0.0001 + 0.0004,      # flash
        LLMPlatform.DEEPSEEK: 0.00014 + 0.00028,  # chat
    }
    rate = cost_per_1k_tokens.get(platform, 0.001)
    return (tokens / 1000) * rate
