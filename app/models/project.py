"""
Project model — represents a user's website to track.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "example.com"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Google integrations
    gsc_property_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ga4_property_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Tracking settings
    target_country: Mapped[str] = mapped_column(String(5), default="US")
    target_language: Mapped[str] = mapped_column(String(5), default="en")
    track_mobile: Mapped[bool] = mapped_column(Boolean, default=True)
    track_desktop: Mapped[bool] = mapped_column(Boolean, default=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner = relationship("User", back_populates="projects")
    competitors = relationship("Competitor", back_populates="project", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
