"""
User model — authentication and profile.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class PlanTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Auth
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_provider: Mapped[str] = mapped_column(String(20), default="email")  # email | google

    # Google tokens (encrypted in production)
    google_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Billing
    plan: Mapped[str] = mapped_column(
        SAEnum("free", "starter", "pro", "agency", name="plan_tier", create_type=False),
        default="free",
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

    @property
    def plan_limits(self) -> dict:
        limits = {
            PlanTier.FREE: {"projects": 1, "competitors": 2, "keywords": 20},
            PlanTier.STARTER: {"projects": 1, "competitors": 3, "keywords": 50},
            PlanTier.PRO: {"projects": 5, "competitors": 10, "keywords": 300},
            PlanTier.AGENCY: {"projects": 20, "competitors": 50, "keywords": 2000},
        }
        return limits.get(self.plan, limits[PlanTier.FREE])
