"""
Celery application — task queue for all agents.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "seo_tracker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.agents"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,   # 5 min soft limit
    task_time_limit=600,        # 10 min hard limit
    task_default_retry_delay=60,
    task_max_retries=3,
)

# ── Beat Schedule: Agent Cron Jobs ─────────────────
celery_app.conf.beat_schedule = {
    # SERP rank tracking — daily 06:00 UTC
    "rank-tracker-daily": {
        "task": "app.tasks.agents.run_rank_tracker",
        "schedule": crontab(hour=6, minute=0),
    },

    # Website change detection — daily 07:00 UTC
    "change-detection-daily": {
        "task": "app.tasks.agents.run_change_detection",
        "schedule": crontab(hour=7, minute=0),
    },

    # GEO: AI visibility tracking — weekly Monday 05:00 UTC
    "geo-visibility-weekly": {
        "task": "app.tasks.agents.run_geo_visibility",
        "schedule": crontab(hour=5, minute=0, day_of_week=1),
    },

    # AI analysis — daily 08:00 UTC (after all data is collected)
    "analysis-daily": {
        "task": "app.tasks.agents.run_analysis",
        "schedule": crontab(hour=8, minute=0),
    },
}

# Tasks are included via 'include' parameter above
