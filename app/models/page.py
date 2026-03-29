"""
Page tracking models — snapshots and change log.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, ForeignKey, Text, Boolean, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class TrackedPage(Base):
    """A specific page on a competitor's site to monitor for changes."""
    __tablename__ = "tracked_pages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    competitor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # "Homepage", "Pricing", etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    competitor = relationship("Competitor", back_populates="tracked_pages")
    snapshots = relationship("PageSnapshot", back_populates="tracked_page", cascade="all, delete-orphan")
    changes = relationship("ChangeLog", back_populates="tracked_page", cascade="all, delete-orphan")


class PageSnapshot(Base):
    """A point-in-time capture of a tracked page's SEO-relevant elements."""
    __tablename__ = "page_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tracked_page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracked_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Extracted SEO data
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    h1: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    headings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {h2: [...], h3: [...]}
    word_count: Mapped[int | None] = mapped_column(nullable=True)
    internal_links_count: Mapped[int | None] = mapped_column(nullable=True)
    external_links_count: Mapped[int | None] = mapped_column(nullable=True)
    schema_markup: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 of body text
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # full page text (compressed?)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    tracked_page = relationship("TrackedPage", back_populates="snapshots")


class ChangeSeverity(str, enum.Enum):
    MINOR = "minor"        # typos, style changes
    MODERATE = "moderate"  # content updates, new sections
    MAJOR = "major"        # structural changes, new pages, complete rewrites


class ChangeLog(Base):
    """A detected change between two snapshots."""
    __tablename__ = "change_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tracked_page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracked_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_before_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("page_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    snapshot_after_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("page_snapshots.id", ondelete="SET NULL"), nullable=True
    )

    severity: Mapped[str] = mapped_column(
        SAEnum(ChangeSeverity, name="change_severity"), default=ChangeSeverity.MINOR
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # title, meta, content, structure, schema
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI analysis
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_impact_score: Mapped[float | None] = mapped_column(nullable=True)  # 0-10

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    tracked_page = relationship("TrackedPage", back_populates="changes")
