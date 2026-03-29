"""
Keyword model — keywords to track, and their rank history.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, ForeignKey, Integer, Float, Text, Boolean, Date,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="keywords")
    ranks = relationship("RankHistory", back_populates="keyword", cascade="all, delete-orphan")


class RankHistory(Base):
    """
    Daily rank snapshot for a keyword × domain.
    One row per keyword × domain × device × date.
    """
    __tablename__ = "rank_history"
    __table_args__ = (
        UniqueConstraint("keyword_id", "domain", "device", "checked_date", name="uq_rank_snapshot"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    keyword_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null = not in top 100
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # ranking URL
    device: Mapped[str] = mapped_column(String(10), default="desktop")  # desktop | mobile
    serp_features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: featured_snippet, etc.

    # Delta (computed on insert)
    position_change: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # GSC data (enriched by Google Data Agent)
    gsc_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gsc_impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gsc_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    gsc_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    checked_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    keyword = relationship("Keyword", back_populates="ranks")
