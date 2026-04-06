"""
Competitor and Keyword CRUD endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.competitor import Competitor
from app.models.keyword import Keyword
from app.schemas.project import (
    CompetitorCreate, CompetitorResponse,
    KeywordCreate, KeywordBulkCreate, KeywordResponse,
)

router = APIRouter(tags=["competitors & keywords"])


# ── Helpers ───────────────────────────────────────────

async def _get_user_project(db: AsyncSession, project_id: str, user_id: str) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# ══════════════════════════════════════════════════════
# COMPETITORS
# ══════════════════════════════════════════════════════

@router.get("/projects/{project_id}/competitors", response_model=List[CompetitorResponse])
async def list_competitors(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_user_project(db, project_id, current_user.id)
    result = await db.execute(
        select(Competitor)
        .where(Competitor.project_id == project_id)
        .order_by(Competitor.created_at)
    )
    return [CompetitorResponse.model_validate(c) for c in result.scalars().all()]


@router.post(
    "/projects/{project_id}/competitors",
    response_model=CompetitorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_competitor(
    project_id: str,
    body: CompetitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(db, project_id, current_user.id)

    # Check plan limits
    existing = await db.scalar(
        select(func.count(Competitor.id)).where(Competitor.project_id == project_id)
    )
    limit = current_user.plan_limits["competitors"]
    if existing >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan limit reached: {limit} competitor(s). Upgrade to add more.",
        )

    domain = body.domain.lower().strip()
    for prefix in ["https://", "http://", "www."]:
        domain = domain.removeprefix(prefix)
    domain = domain.rstrip("/")

    competitor = Competitor(
        project_id=project_id,
        domain=domain,
        name=body.name,
        notes=body.notes,
    )
    db.add(competitor)
    await db.flush()
    return CompetitorResponse.model_validate(competitor)


@router.delete("/competitors/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    # Verify ownership
    await _get_user_project(db, competitor.project_id, current_user.id)
    await db.delete(competitor)


# ══════════════════════════════════════════════════════
# KEYWORDS
# ══════════════════════════════════════════════════════

@router.get("/projects/{project_id}/keywords", response_model=List[KeywordResponse])
async def list_keywords(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_user_project(db, project_id, current_user.id)
    result = await db.execute(
        select(Keyword)
        .where(Keyword.project_id == project_id)
        .order_by(Keyword.created_at)
    )
    return [KeywordResponse.model_validate(k) for k in result.scalars().all()]


@router.post(
    "/projects/{project_id}/keywords",
    response_model=KeywordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_keyword(
    project_id: str,
    body: KeywordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_user_project(db, project_id, current_user.id)
    await _check_keyword_limit(db, project_id, current_user, 1)

    kw = Keyword(
        project_id=project_id,
        keyword=body.keyword.strip(),
        tags=body.tags,
    )
    db.add(kw)
    await db.flush()
    return KeywordResponse.model_validate(kw)


@router.post(
    "/projects/{project_id}/keywords/bulk",
    response_model=List[KeywordResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_add_keywords(
    project_id: str,
    body: KeywordBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_user_project(db, project_id, current_user.id)
    await _check_keyword_limit(db, project_id, current_user, len(body.keywords))

    # Deduplicate
    existing_result = await db.execute(
        select(Keyword.keyword).where(Keyword.project_id == project_id)
    )
    existing_kws = {row[0].lower() for row in existing_result.all()}

    new_keywords = []
    for kw_text in body.keywords:
        clean = kw_text.strip()
        if clean.lower() not in existing_kws:
            kw = Keyword(project_id=project_id, keyword=clean, tags=body.tags)
            db.add(kw)
            new_keywords.append(kw)
            existing_kws.add(clean.lower())

    await db.flush()
    return [KeywordResponse.model_validate(k) for k in new_keywords]


@router.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await _get_user_project(db, kw.project_id, current_user.id)
    await db.delete(kw)


async def _check_keyword_limit(
    db: AsyncSession, project_id: str, user: User, adding: int
):
    existing = await db.scalar(
        select(func.count(Keyword.id)).where(Keyword.project_id == project_id)
    )
    limit = user.plan_limits["keywords"]
    if (existing + adding) > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan limit: {limit} keywords. You have {existing}, trying to add {adding}. Upgrade to continue.",
        )


# ── Tracked Pages ─────────────────────────────────────

from app.models.page import TrackedPage
from app.schemas.project import TrackedPageCreate, TrackedPageResponse


@router.get(
    "/competitors/{competitor_id}/pages",
    response_model=List[TrackedPageResponse],
)
async def list_tracked_pages(
    competitor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TrackedPage).where(TrackedPage.competitor_id == competitor_id)
    )
    return [TrackedPageResponse.model_validate(p) for p in result.scalars().all()]


@router.post(
    "/competitors/{competitor_id}/pages",
    response_model=TrackedPageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_tracked_page(
    competitor_id: str,
    body: TrackedPageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify competitor exists
    comp = await db.get(Competitor, competitor_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    page = TrackedPage(
        competitor_id=competitor_id,
        url=body.url.strip(),
        label=body.label,
    )
    db.add(page)
    await db.flush()
    return TrackedPageResponse.model_validate(page)


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracked_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(TrackedPage).where(TrackedPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Tracked page not found")
    await db.delete(page)
