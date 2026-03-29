"""
Agent run tracking — logs each agent execution.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class AgentType(str, enum.Enum):
    RANK_TRACKER = "rank_tracker"
    CHANGE_DETECTION = "change_detection"
    GOOGLE_DATA = "google_data"
    GEO_VISIBILITY = "geo_visibility"
    ANALYSIS = "analysis"
    ALERT_REPORT = "alert_report"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(Base):
    """Logs each execution of an agent for observability."""
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_type: Mapped[str] = mapped_column(
        SAEnum(AgentType, name="agent_type"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        SAEnum(RunStatus, name="run_status"), default=RunStatus.PENDING
    )

    # Stats
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    api_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Output
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
