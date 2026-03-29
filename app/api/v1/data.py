"""
Data API endpoints — rank history, changes feed, dashboard stats.
Serves data to frontend charts and tables.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.keyword import Keyword, RankHistory
from app.models.competitor import Competitor
from app.models.page import ChangeLog, TrackedPage

router = APIRouter(prefix="/data", tags=["data"])


# ── Schemas ───────────────────────────────────────────

class RankPointResponse(BaseModel):
    date: str
    positions: dict[str, int | None]  # {domain: position}


class RankHistoryResponse(BaseModel):
    keyword: str
    keyword_id: str
    domains: list[str]
    data: list[RankPointResponse]


class ChangeEntryResponse(BaseModel):
    id: str
    competitor_name: str
    competitor_domain: str
    page_url: str
    severity: str
    change_type: str
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    ai_summary: Optional[str]
    detected_at: str


class DashboardStatsResponse(BaseModel):
    total_keywords: int
    total_competitors: int
    avg_position: Optional[float]
    keywords_improved: int
    keywords_declined: int
    changes_today: int
    last_agent_run: Optional[str]


# ── Helpers ───────────────────────────────────────────

async def _verify_project(db: AsyncSession, project_id: str, user_id: str) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Rank History (for charts) ─────────────────────────

@router.get("/projects/{project_id}/rank-history/{keyword_id}", response_model=RankHistoryResponse)
async def get_rank_history(
    project_id: str,
    keyword_id: str,
    days: int = Query(30, le=90),
    device: str = Query("desktop"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get rank history for a keyword — data for the position chart."""
    project = await _verify_project(db, project_id, current_user.id)

    # Verify keyword belongs to project
    kw_result = await db.execute(
        select(Keyword).where(Keyword.id == keyword_id, Keyword.project_id == project_id)
    )
    keyword = kw_result.scalar_one_or_none()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    since = date.today() - timedelta(days=days)

    # Fetch all rank entries for this keyword
    ranks = await db.execute(
        select(RankHistory)
        .where(and_(
            RankHistory.keyword_id == keyword_id,
            RankHistory.device == device,
            RankHistory.checked_date >= since,
        ))
        .order_by(RankHistory.checked_date)
    )
    rank_rows = ranks.scalars().all()

    # Build domain list: project domain + competitor domains
    domains = [project.domain]
    comp_result = await db.execute(
        select(Competitor.domain).where(Competitor.project_id == project_id, Competitor.is_active == True)
    )
    for row in comp_result.all():
        domains.append(row[0])

    # Group by date
    date_data: dict[str, dict[str, int | None]] = {}
    for r in rank_rows:
        d_str = r.checked_date.isoformat() if hasattr(r.checked_date, 'isoformat') else str(r.checked_date)
        if d_str not in date_data:
            date_data[d_str] = {}
        date_data[d_str][r.domain] = r.position

    data = []
    for d_str in sorted(date_data.keys()):
        data.append(RankPointResponse(
            date=d_str,
            positions=date_data[d_str],
        ))

    return RankHistoryResponse(
        keyword=keyword.keyword,
        keyword_id=keyword.id,
        domains=domains,
        data=data,
    )


# ── Changes Feed ──────────────────────────────────────

@router.get("/projects/{project_id}/changes", response_model=List[ChangeEntryResponse])
async def get_changes_feed(
    project_id: str,
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent changes detected on competitor websites."""
    project = await _verify_project(db, project_id, current_user.id)

    # Get all competitor IDs for this project
    comp_result = await db.execute(
        select(Competitor).where(Competitor.project_id == project_id)
    )
    competitors = {c.id: c for c in comp_result.scalars().all()}
    comp_ids = list(competitors.keys())

    if not comp_ids:
        return []

    # Get tracked page IDs for these competitors
    page_result = await db.execute(
        select(TrackedPage).where(TrackedPage.competitor_id.in_(comp_ids))
    )
    pages = {p.id: p for p in page_result.scalars().all()}
    page_ids = list(pages.keys())

    if not page_ids:
        return []

    # Fetch changes
    query = (
        select(ChangeLog)
        .where(ChangeLog.tracked_page_id.in_(page_ids))
        .order_by(desc(ChangeLog.detected_at))
        .limit(limit)
    )
    if severity:
        query = query.where(ChangeLog.severity == severity)

    changes_result = await db.execute(query)
    changes = changes_result.scalars().all()

    result = []
    for ch in changes:
        page = pages.get(ch.tracked_page_id)
        comp = competitors.get(page.competitor_id) if page else None
        result.append(ChangeEntryResponse(
            id=ch.id,
            competitor_name=comp.name if comp else "Unknown",
            competitor_domain=comp.domain if comp else "",
            page_url=page.url if page else "",
            severity=ch.severity.value if hasattr(ch.severity, "value") else str(ch.severity),
            change_type=ch.change_type,
            field_name=ch.field_name,
            old_value=ch.old_value[:500] if ch.old_value else None,
            new_value=ch.new_value[:500] if ch.new_value else None,
            ai_summary=ch.ai_summary,
            detected_at=ch.detected_at.isoformat(),
        ))

    return result


# ── Dashboard Stats ───────────────────────────────────

@router.get("/projects/{project_id}/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated stats for the project dashboard."""
    project = await _verify_project(db, project_id, current_user.id)
    today = date.today()

    # Keyword count
    total_kw = await db.scalar(
        select(func.count(Keyword.id)).where(Keyword.project_id == project_id)
    ) or 0

    # Competitor count
    total_comp = await db.scalar(
        select(func.count(Competitor.id)).where(Competitor.project_id == project_id)
    ) or 0

    # Today's rank data for own domain
    today_ranks = await db.execute(
        select(RankHistory)
        .join(Keyword)
        .where(and_(
            Keyword.project_id == project_id,
            RankHistory.domain == project.domain,
            RankHistory.checked_date == today,
        ))
    )
    today_rows = today_ranks.scalars().all()

    positions = [r.position for r in today_rows if r.position is not None]
    avg_pos = round(sum(positions) / len(positions), 1) if positions else None

    improved = sum(1 for r in today_rows if r.position_change and r.position_change > 0)
    declined = sum(1 for r in today_rows if r.position_change and r.position_change < 0)

    # Changes today
    comp_result = await db.execute(
        select(Competitor.id).where(Competitor.project_id == project_id)
    )
    comp_ids = [r[0] for r in comp_result.all()]
    changes_today = 0
    if comp_ids:
        page_result = await db.execute(
            select(TrackedPage.id).where(TrackedPage.competitor_id.in_(comp_ids))
        )
        page_ids = [r[0] for r in page_result.all()]
        if page_ids:
            changes_today = await db.scalar(
                select(func.count(ChangeLog.id)).where(and_(
                    ChangeLog.tracked_page_id.in_(page_ids),
                    ChangeLog.detected_at >= datetime.combine(today, datetime.min.time()),
                ))
            ) or 0

    # Last agent run
    from app.models.agent_run import AgentRun
    last_run = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(desc(AgentRun.started_at))
        .limit(1)
    )
    last = last_run.scalar_one_or_none()

    return DashboardStatsResponse(
        total_keywords=total_kw,
        total_competitors=total_comp,
        avg_position=avg_pos,
        keywords_improved=improved,
        keywords_declined=declined,
        changes_today=changes_today,
        last_agent_run=last.started_at.isoformat() if last else None,
    )
