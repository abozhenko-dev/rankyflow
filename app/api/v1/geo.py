"""
GEO / AI Visibility API endpoints.
Manage prompts, view visibility data, trigger on-demand checks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, PlanTier
from app.models.project import Project
from app.models.geo import (
    LLMPrompt, LLMResponse, LLMMention, GEOVisibilitySnapshot,
    LLMPlatform, PromptIntent,
)

router = APIRouter(prefix="/geo", tags=["geo / ai visibility"])


# ── Schemas ───────────────────────────────────────────

class PromptCreate(BaseModel):
    prompt_text: str = Field(max_length=2000)
    intent: str = "commercial"
    tags: Optional[str] = None


class PromptBulkCreate(BaseModel):
    prompts: List[str] = Field(min_length=1, max_length=100)
    intent: str = "commercial"


class PromptResponse(BaseModel):
    id: str
    prompt_text: str
    intent: str
    tags: Optional[str]
    is_active: bool
    is_auto_generated: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class VisibilitySnapshotResponse(BaseModel):
    platform: str
    mention_rate: float
    citation_rate: float
    recommendation_rate: float
    avg_position: Optional[float]
    share_of_voice: float
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    snapshot_date: date
    model_config = {"from_attributes": True}


class MentionDetailResponse(BaseModel):
    prompt_text: str
    platform: str
    domain: str
    brand_name: str
    is_mentioned: bool
    is_cited: bool
    is_recommended: bool
    position_in_list: Optional[int]
    sentiment: Optional[str]
    checked_date: date


# ── Helpers ───────────────────────────────────────────

def _require_geo_access(user: User):
    """GEO features available on all plans for now."""
    pass  # All plans have access


async def _get_user_project(db: AsyncSession, project_id: str, user_id: str) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Prompt Management ─────────────────────────────────

@router.get("/projects/{project_id}/prompts", response_model=List[PromptResponse])
async def list_prompts(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_geo_access(current_user)
    await _get_user_project(db, project_id, current_user.id)

    result = await db.execute(
        select(LLMPrompt)
        .where(LLMPrompt.project_id == project_id)
        .order_by(LLMPrompt.created_at)
    )
    return [PromptResponse.model_validate(p) for p in result.scalars().all()]


@router.post(
    "/projects/{project_id}/prompts",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_prompt(
    project_id: str,
    body: PromptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_geo_access(current_user)
    await _get_user_project(db, project_id, current_user.id)
    await _check_prompt_limit(db, project_id, current_user, 1)

    prompt = LLMPrompt(
        project_id=project_id,
        prompt_text=body.prompt_text.strip(),
        intent=body.intent,
        tags=body.tags,
    )
    db.add(prompt)
    await db.flush()
    return PromptResponse.model_validate(prompt)


@router.post(
    "/projects/{project_id}/prompts/bulk",
    response_model=List[PromptResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_add_prompts(
    project_id: str,
    body: PromptBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_geo_access(current_user)
    await _get_user_project(db, project_id, current_user.id)
    await _check_prompt_limit(db, project_id, current_user, len(body.prompts))

    created = []
    for text in body.prompts:
        prompt = LLMPrompt(
            project_id=project_id,
            prompt_text=text.strip(),
            intent=body.intent,
        )
        db.add(prompt)
        created.append(prompt)

    await db.flush()
    return [PromptResponse.model_validate(p) for p in created]


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_geo_access(current_user)
    result = await db.execute(select(LLMPrompt).where(LLMPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await _get_user_project(db, prompt.project_id, current_user.id)
    await db.delete(prompt)


# ── Visibility Data ───────────────────────────────────

@router.get(
    "/projects/{project_id}/visibility",
    response_model=List[VisibilitySnapshotResponse],
)
async def get_visibility_snapshots(
    project_id: str,
    platform: Optional[str] = None,
    limit: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated visibility snapshots (for trend charts)."""
    _require_geo_access(current_user)
    await _get_user_project(db, project_id, current_user.id)

    query = (
        select(GEOVisibilitySnapshot)
        .where(GEOVisibilitySnapshot.project_id == project_id)
        .order_by(GEOVisibilitySnapshot.snapshot_date.desc())
        .limit(limit)
    )
    if platform:
        query = query.where(GEOVisibilitySnapshot.platform == platform)

    result = await db.execute(query)
    return [VisibilitySnapshotResponse.model_validate(s) for s in result.scalars().all()]


# ── Prompt Limits ─────────────────────────────────────

GEO_PROMPT_LIMITS = {
    "free": 10,
    "starter": 25,
    "pro": 50,
    "agency": 200,
}

async def _check_prompt_limit(db: AsyncSession, project_id: str, user: User, adding: int):
    limit = GEO_PROMPT_LIMITS.get(user.plan, 0)
    existing = await db.scalar(
        select(func.count(LLMPrompt.id)).where(LLMPrompt.project_id == project_id)
    )
    if (existing + adding) > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"GEO prompt limit: {limit}. You have {existing}, trying to add {adding}.",
        )
