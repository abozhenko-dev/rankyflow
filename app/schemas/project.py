"""
Project, Competitor, and Keyword schemas.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


# ── Projects ──────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(max_length=255)
    domain: str = Field(max_length=255, examples=["example.com"])
    description: Optional[str] = None
    target_country: str = Field(default="US", max_length=5)
    target_language: str = Field(default="en", max_length=5)
    track_mobile: bool = True
    track_desktop: bool = True
    gsc_property_url: Optional[str] = None
    ga4_property_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_country: Optional[str] = None
    target_language: Optional[str] = None
    track_mobile: Optional[bool] = None
    track_desktop: Optional[bool] = None
    gsc_property_url: Optional[str] = None
    ga4_property_id: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    domain: str
    description: Optional[str]
    target_country: str
    target_language: str
    track_mobile: bool
    track_desktop: bool
    gsc_property_url: Optional[str]
    ga4_property_id: Optional[str]
    is_active: bool
    created_at: datetime
    competitors_count: int = 0
    keywords_count: int = 0

    model_config = {"from_attributes": True}


# ── Competitors ───────────────────────────────────────

class CompetitorCreate(BaseModel):
    domain: str = Field(max_length=255, examples=["competitor.com"])
    name: str = Field(max_length=255, examples=["Competitor Inc"])
    notes: Optional[str] = None


class CompetitorResponse(BaseModel):
    id: str
    project_id: str
    domain: str
    name: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Keywords ──────────────────────────────────────────

class KeywordCreate(BaseModel):
    keyword: str = Field(max_length=500)
    tags: Optional[str] = None


class KeywordBulkCreate(BaseModel):
    """Import multiple keywords at once (CSV-style)."""
    keywords: List[str] = Field(min_length=1, max_length=500)
    tags: Optional[str] = None


class KeywordResponse(BaseModel):
    id: str
    project_id: str
    keyword: str
    search_volume: Optional[int]
    difficulty: Optional[float]
    tags: Optional[str]
    is_active: bool
    created_at: datetime
    latest_position: Optional[int] = None
    position_change: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Tracked Pages ─────────────────────────────────────

class TrackedPageCreate(BaseModel):
    url: str = Field(max_length=2000)
    label: Optional[str] = Field(default=None, max_length=255)


class TrackedPageResponse(BaseModel):
    id: str
    competitor_id: str
    url: str
    label: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
