"""
Analysis Agent — uses Claude to correlate rank changes, site changes, and GEO data.
Generates daily digests with insights and recommendations.
"""
import json
import time
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import select, and_, func
import structlog
import httpx

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.project import Project
from app.models.keyword import RankHistory
from app.models.page import ChangeLog
from app.models.geo import GEOVisibilitySnapshot, LLMPlatform
from app.models.agent_run import AgentRun, AgentType, RunStatus

logger = structlog.get_logger()


def run(project_id: str | None = None):
    """Main entry point for Analysis Agent."""
    started = time.time()

    with get_sync_db() as db:
        query = select(Project).where(Project.is_active == True)
        if project_id:
            query = query.where(Project.id == project_id)

        projects = db.execute(query).scalars().all()
        total_processed = 0

        for project in projects:
            try:
                _analyze_project(db, project)
                total_processed += 1
            except Exception as e:
                logger.error("Analysis failed", project_id=project.id, error=str(e))

        duration = time.time() - started
        run_log = AgentRun(
            project_id=project_id or "all",
            agent_type=AgentType.ANALYSIS,
            status=RunStatus.COMPLETED,
            items_processed=total_processed,
            duration_seconds=round(duration, 2),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_log)

    logger.info("🧠 Analysis Agent completed",
                projects=total_processed, duration=f"{duration:.1f}s")


def _analyze_project(db, project: Project):
    """Gather data from all agents and run Claude analysis."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 1. Gather rank changes (today's significant movements)
    rank_changes = db.execute(
        select(RankHistory)
        .join(RankHistory.keyword)
        .where(and_(
            RankHistory.checked_date == today,
            RankHistory.position_change != None,
            func.abs(RankHistory.position_change) >= 3,
        ))
        .where(RankHistory.keyword.has(project_id=project.id))
        .limit(50)
    ).scalars().all()

    rank_summary = []
    for rh in rank_changes:
        rank_summary.append({
            "keyword": rh.keyword.keyword if rh.keyword else "?",
            "domain": rh.domain,
            "position": rh.position,
            "change": rh.position_change,
            "device": rh.device,
        })

    # 2. Gather recent site changes (last 24h)
    recent_changes = db.execute(
        select(ChangeLog)
        .where(ChangeLog.detected_at >= datetime.combine(yesterday, datetime.min.time()))
        .join(ChangeLog.tracked_page)
        .limit(30)
    ).scalars().all()

    changes_summary = []
    for ch in recent_changes:
        changes_summary.append({
            "url": ch.tracked_page.url if ch.tracked_page else "?",
            "field": ch.field_name,
            "type": ch.change_type,
            "severity": ch.severity.value if hasattr(ch.severity, 'value') else ch.severity,
            "old": (ch.old_value or "")[:200],
            "new": (ch.new_value or "")[:200],
        })

    # 3. Latest GEO visibility (if available)
    geo_data = db.execute(
        select(GEOVisibilitySnapshot)
        .where(GEOVisibilitySnapshot.project_id == project.id)
        .order_by(GEOVisibilitySnapshot.snapshot_date.desc())
        .limit(5)
    ).scalars().all()

    geo_summary = []
    for gs in geo_data:
        geo_summary.append({
            "platform": gs.platform.value if hasattr(gs.platform, 'value') else gs.platform,
            "mention_rate": gs.mention_rate,
            "citation_rate": gs.citation_rate,
            "share_of_voice": gs.share_of_voice,
            "avg_position": gs.avg_position,
            "date": gs.snapshot_date.isoformat(),
        })

    # 4. Skip if no data to analyze
    if not rank_summary and not changes_summary and not geo_summary:
        logger.info("No data to analyze", project=project.domain)
        return

    # 5. Build Claude prompt
    prompt = _build_analysis_prompt(project, rank_summary, changes_summary, geo_summary)

    # 6. Call Claude API
    import asyncio
    analysis = asyncio.run(_call_claude(prompt))

    if not analysis:
        return

    # 7. Save analysis as agent run result
    run_log = AgentRun(
        project_id=project.id,
        agent_type=AgentType.ANALYSIS,
        status=RunStatus.COMPLETED,
        items_processed=len(rank_summary) + len(changes_summary),
        result_summary=json.dumps(analysis, ensure_ascii=False),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(run_log)

    logger.info("Analysis generated", project=project.domain,
                insights=len(analysis.get("insights", [])))


def _build_analysis_prompt(
    project: Project,
    rank_changes: list[dict],
    site_changes: list[dict],
    geo_data: list[dict],
) -> str:
    return f"""You are an SEO analyst AI. Analyze the following data for the website "{project.domain}" and provide actionable insights.

## SERP Position Changes (today)
{json.dumps(rank_changes, indent=2, ensure_ascii=False) if rank_changes else "No significant changes today."}

## Competitor Website Changes (last 24h)
{json.dumps(site_changes, indent=2, ensure_ascii=False) if site_changes else "No changes detected."}

## AI Visibility / GEO Data (latest)
{json.dumps(geo_data, indent=2, ensure_ascii=False) if geo_data else "No GEO data available."}

## Instructions
Respond ONLY with a JSON object (no markdown, no backticks) with this exact structure:
{{
  "summary": "2-3 sentence overview of today's situation",
  "severity": "low|medium|high|critical",
  "insights": [
    {{
      "type": "rank_change|competitor_update|geo_shift|correlation",
      "title": "Short insight title",
      "description": "What happened and why it matters",
      "impact": "low|medium|high"
    }}
  ],
  "recommendations": [
    {{
      "priority": 1,
      "action": "Specific action to take",
      "reason": "Why this matters",
      "effort": "low|medium|high"
    }}
  ],
  "correlations": [
    {{
      "observation": "Describe a correlation found between rank changes and site changes or GEO shifts"
    }}
  ]
}}

Focus on:
- Correlations between competitor site changes and ranking movements
- Patterns in which competitors are gaining/losing positions
- AI visibility trends and which platforms show brand presence
- Actionable recommendations prioritized by impact vs effort
"""


async def _call_claude(prompt: str) -> dict | None:
    """Call Claude API and parse structured response."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data["content"][0]["text"]

        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        return json.loads(text)

    except (json.JSONDecodeError, KeyError, httpx.HTTPError) as e:
        logger.error("Claude analysis call failed", error=str(e))
        return None
