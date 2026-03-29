"""
Agent tasks — Celery entry points calling real agent logic.
Each task wraps the corresponding agent module with error handling.
"""
import structlog
from app.tasks import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.agents.run_rank_tracker",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def run_rank_tracker(self, project_id: str | None = None):
    """Rank Tracker Agent — daily 06:00 UTC."""
    logger.info("🎯 Rank Tracker Agent starting")
    try:
        from app.agents.rank_tracker import run
        run(project_id)
    except Exception as exc:
        logger.error("🎯 Rank Tracker Agent failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.agents.run_change_detection",
    bind=True,
    max_retries=2,
    default_retry_delay=180,
)
def run_change_detection(self, project_id: str | None = None):
    """Change Detection Agent — daily 07:00 UTC."""
    logger.info("🕵️ Change Detection Agent starting")
    try:
        from app.agents.change_detection import run
        run(project_id)
    except Exception as exc:
        logger.error("🕵️ Change Detection Agent failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.agents.run_google_data_sync",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def run_google_data_sync(self, project_id: str | None = None):
    """Google Data Agent — daily 07:30 UTC."""
    logger.info("📊 Google Data Agent starting")
    try:
        # TODO: implement after GSC/GA4 service is built
        logger.info("📊 Google Data Agent — not yet implemented, skipping")
    except Exception as exc:
        logger.error("📊 Google Data Agent failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.agents.run_geo_visibility",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=600,
    time_limit=900,
)
def run_geo_visibility(self, project_id: str | None = None):
    """GEO Visibility Agent — weekly Monday 05:00 UTC."""
    logger.info("👁️ GEO Visibility Agent starting")
    try:
        from app.agents.geo_visibility import run
        run(project_id)
    except Exception as exc:
        logger.error("👁️ GEO Visibility Agent failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.agents.run_analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def run_analysis(self, project_id: str | None = None):
    """Analysis Agent — daily 08:00 UTC."""
    logger.info("🧠 Analysis Agent starting")
    try:
        from app.agents.analysis import run
        run(project_id)
    except Exception as exc:
        logger.error("🧠 Analysis Agent failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.agents.run_alert_report",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_alert_report(self, project_id: str | None = None):
    """Alert & Report Agent — daily 08:30 UTC."""
    logger.info("📢 Alert & Report Agent starting")
    try:
        from app.agents.alert_report import run
        run(project_id)
    except Exception as exc:
        logger.error("📢 Alert & Report Agent failed", error=str(exc))
        raise self.retry(exc=exc)


# ── Manual trigger ────────────────────────────────────

@celery_app.task(name="app.tasks.agents.run_all_for_project")
def run_all_for_project(project_id: str):
    """Run all agents sequentially for a specific project (on-demand)."""
    logger.info("Running all agents for project", project_id=project_id)
    run_rank_tracker.delay(project_id)
    run_change_detection.delay(project_id)
    run_google_data_sync.delay(project_id)
    run_geo_visibility.delay(project_id)
    run_analysis.apply_async(args=[project_id], countdown=120)
    run_alert_report.apply_async(args=[project_id], countdown=180)
