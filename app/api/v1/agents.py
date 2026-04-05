"""
Agent control endpoints — manual triggers, run history.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.agent_run import AgentRun, AgentType

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunResponse(BaseModel):
    id: str
    project_id: str
    agent_type: str
    status: str
    items_processed: int
    items_failed: int
    duration_seconds: Optional[float]
    api_cost_usd: Optional[float]
    result_summary: Optional[str]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TriggerResponse(BaseModel):
    message: str
    task_id: str


@router.post("/projects/{project_id}/run-all", response_model=TriggerResponse)
async def trigger_all_agents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger all agents for a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    from app.tasks.agents import run_all_for_project
    task = run_all_for_project.delay(project_id)

    return TriggerResponse(
        message="All agents queued for execution",
        task_id=task.id,
    )


@router.post("/projects/{project_id}/run/{agent_type}", response_model=TriggerResponse)
async def trigger_single_agent(
    project_id: str,
    agent_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a specific agent for a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    from app.tasks import agents as agent_tasks

    task_map = {
        "rank_tracker": agent_tasks.run_rank_tracker,
        "change_detection": agent_tasks.run_change_detection,
        "google_data": agent_tasks.run_google_data_sync,
        "geo_visibility": agent_tasks.run_geo_visibility,
        "analysis": agent_tasks.run_analysis,
        "alert_report": agent_tasks.run_alert_report,
    }

    task_fn = task_map.get(agent_type)
    if not task_fn:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent type: {agent_type}. Valid: {list(task_map.keys())}",
        )

    task = task_fn.delay(project_id)
    return TriggerResponse(message=f"Agent '{agent_type}' queued", task_id=task.id)


@router.get("/projects/{project_id}/runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    project_id: str,
    agent_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get agent run history for a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    query = (
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
    )
    if agent_type:
        query = query.where(AgentRun.agent_type == agent_type)

    runs = await db.execute(query)
    return [AgentRunResponse.model_validate(r) for r in runs.scalars().all()]


@router.get("/debug/worker-ip")
async def debug_worker_ip(user: User = Depends(get_current_user)):
    """Trigger worker IP check and return task ID."""
    from app.tasks.agents import check_worker_ip
    task = check_worker_ip.delay()
    return {"task_id": str(task.id), "message": "Check worker logs for IP"}
