"""
Project CRUD endpoints.
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
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.owner_id == current_user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    responses = []
    for p in projects:
        comp_count = await db.scalar(
            select(func.count(Competitor.id)).where(Competitor.project_id == p.id)
        )
        kw_count = await db.scalar(
            select(func.count(Keyword.id)).where(Keyword.project_id == p.id)
        )
        resp = ProjectResponse.model_validate(p)
        resp.competitors_count = comp_count or 0
        resp.keywords_count = kw_count or 0
        responses.append(resp)

    return responses


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check plan limits
    existing_count = await db.scalar(
        select(func.count(Project.id)).where(Project.owner_id == current_user.id)
    )
    limit = current_user.plan_limits["projects"]
    if existing_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan limit reached: {limit} project(s). Upgrade to add more.",
        )

    # Clean domain
    domain = body.domain.lower().strip()
    for prefix in ["https://", "http://", "www."]:
        domain = domain.removeprefix(prefix)
    domain = domain.rstrip("/")

    project = Project(
        owner_id=current_user.id,
        name=body.name,
        domain=domain,
        description=body.description,
        target_country=body.target_country,
        target_language=body.target_language,
        track_mobile=body.track_mobile,
        track_desktop=body.track_desktop,
        gsc_property_url=body.gsc_property_url,
        ga4_property_id=body.ga4_property_id,
    )
    db.add(project)
    await db.flush()

    resp = ProjectResponse.model_validate(project)
    resp.competitors_count = 0
    resp.keywords_count = 0
    return resp


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(db, project_id, current_user.id)

    comp_count = await db.scalar(
        select(func.count(Competitor.id)).where(Competitor.project_id == project.id)
    )
    kw_count = await db.scalar(
        select(func.count(Keyword.id)).where(Keyword.project_id == project.id)
    )
    resp = ProjectResponse.model_validate(project)
    resp.competitors_count = comp_count or 0
    resp.keywords_count = kw_count or 0
    return resp


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(db, project_id, current_user.id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(db, project_id, current_user.id)
    await db.delete(project)


# ── Helper ────────────────────────────────────────────

async def _get_user_project(db: AsyncSession, project_id: str, user_id: str) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
