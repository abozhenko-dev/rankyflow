"""
GEO / AI Visibility models — LLM prompt tracking, responses, brand mentions.
Inspired by Peec.ai approach: track brand visibility across AI search platforms.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, ForeignKey, Text, Boolean, Integer, Float,
    Enum as SAEnum, Date, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class LLMPlatform(str, enum.Enum):
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    PERPLEXITY = "perplexity"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


class PromptIntent(str, enum.Enum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class LLMPrompt(Base):
    """
    A prompt (question) to send to AI platforms for brand visibility tracking.
    Example: "What is the best CRM for small business?"
    """
    __tablename__ = "llm_prompts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(
        SAEnum(PromptIntent, name="prompt_intent"), default=PromptIntent.COMMERCIAL
    )
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    responses = relationship("LLMResponse", back_populates="prompt", cascade="all, delete-orphan")


class LLMResponse(Base):
    """
    A single AI platform's response to a prompt at a point in time.
    Stores the full response text + extracted citations.
    """
    __tablename__ = "llm_responses"
    __table_args__ = (
        UniqueConstraint("prompt_id", "platform", "checked_date", name="uq_llm_response"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    prompt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_prompts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(
        SAEnum(LLMPlatform, name="llm_platform"), nullable=False
    )

    # Full response
    response_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Extracted citations / sources (JSON arrays)
    cited_urls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: ["https://...", ...]
    cited_domains: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: ["g2.com", "reddit.com"]
    source_count: Mapped[int] = mapped_column(Integer, default=0)

    # API metadata
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "gpt-4o-mini", "sonar-pro"
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    checked_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    prompt = relationship("LLMPrompt", back_populates="responses")
    mentions = relationship("LLMMention", back_populates="response", cascade="all, delete-orphan")


class LLMMention(Base):
    """
    A brand/competitor mention detected within an LLM response.
    One response can contain multiple mentions (user's brand + N competitors).
    """
    __tablename__ = "llm_mentions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    response_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Visibility metrics
    is_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_cited: Mapped[bool] = mapped_column(Boolean, default=False)  # URL appears in sources
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)  # explicitly recommended
    position_in_list: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1st, 2nd... or null
    mention_count: Mapped[int] = mapped_column(Integer, default=0)  # times mentioned in response

    # Sentiment
    sentiment: Mapped[str | None] = mapped_column(
        SAEnum(Sentiment, name="mention_sentiment"), nullable=True
    )
    sentiment_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # the sentence mentioning brand

    # Is this the user's own brand or a competitor?
    is_own_brand: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    response = relationship("LLMResponse", back_populates="mentions")


class GEOVisibilitySnapshot(Base):
    """
    Aggregated weekly snapshot of AI visibility metrics per project × platform.
    Pre-computed for fast dashboard rendering.
    """
    __tablename__ = "geo_visibility_snapshots"
    __table_args__ = (
        UniqueConstraint("project_id", "platform", "snapshot_date", name="uq_geo_snapshot"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(
        SAEnum(LLMPlatform, name="llm_platform_snap"), nullable=False
    )

    # Aggregated metrics
    total_prompts_checked: Mapped[int] = mapped_column(Integer, default=0)
    mention_rate: Mapped[float] = mapped_column(Float, default=0.0)  # % of prompts where brand mentioned
    citation_rate: Mapped[float] = mapped_column(Float, default=0.0)  # % of prompts where brand URL cited
    recommendation_rate: Mapped[float] = mapped_column(Float, default=0.0)  # % where explicitly recommended
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)  # avg list position when mentioned
    share_of_voice: Mapped[float] = mapped_column(Float, default=0.0)  # vs all tracked competitors

    # Sentiment distribution
    positive_pct: Mapped[float] = mapped_column(Float, default=0.0)
    neutral_pct: Mapped[float] = mapped_column(Float, default=0.0)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Top sources that AI platforms cite (JSON)
    top_source_domains: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [{"domain": "g2.com", "count": 15}, ...]

    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
