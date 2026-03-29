"""
Alert & Report Agent — sends email digests and instant alerts.
Reads analysis results → renders email → sends via Resend + webhooks.
"""
import json
import time
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import select, and_, func
import structlog
import httpx

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.user import User
from app.models.project import Project
from app.models.keyword import RankHistory
from app.models.agent_run import AgentRun, AgentType, RunStatus

logger = structlog.get_logger()

# Alert thresholds
CRITICAL_POSITION_CHANGE = 10  # instant alert
DAILY_DIGEST_THRESHOLD = 3     # include in daily digest


def run(project_id: str | None = None):
    """Main entry point for Alert & Report Agent."""
    started = time.time()

    with get_sync_db() as db:
        query = (
            select(Project)
            .where(Project.is_active == True)
            .join(User, Project.owner_id == User.id)
        )
        if project_id:
            query = query.where(Project.id == project_id)

        projects = db.execute(query).scalars().all()
        emails_sent = 0

        for project in projects:
            try:
                owner = db.execute(
                    select(User).where(User.id == project.owner_id)
                ).scalar_one()

                sent = _process_project(db, project, owner)
                emails_sent += sent
            except Exception as e:
                logger.error("Alert agent failed", project_id=project.id, error=str(e))

        duration = time.time() - started
        run_log = AgentRun(
            project_id=project_id or "all",
            agent_type=AgentType.ALERT_REPORT,
            status=RunStatus.COMPLETED,
            items_processed=emails_sent,
            duration_seconds=round(duration, 2),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_log)

    logger.info("📢 Alert & Report completed",
                emails=emails_sent, duration=f"{duration:.1f}s")


def _process_project(db, project: Project, owner: User) -> int:
    """Check for alerts and send digest for one project."""
    today = date.today()
    sent_count = 0

    # 1. Get today's analysis (from Analysis Agent)
    analysis_run = db.execute(
        select(AgentRun)
        .where(and_(
            AgentRun.project_id == project.id,
            AgentRun.agent_type == AgentType.ANALYSIS,
            AgentRun.started_at >= datetime.combine(today, datetime.min.time()),
        ))
        .order_by(AgentRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    analysis = {}
    if analysis_run and analysis_run.result_summary:
        try:
            analysis = json.loads(analysis_run.result_summary)
        except json.JSONDecodeError:
            pass

    # 2. Check for critical anomalies (instant alert)
    critical_changes = db.execute(
        select(RankHistory)
        .join(RankHistory.keyword)
        .where(and_(
            RankHistory.checked_date == today,
            RankHistory.position_change != None,
            func.abs(RankHistory.position_change) >= CRITICAL_POSITION_CHANGE,
        ))
        .where(RankHistory.keyword.has(project_id=project.id))
    ).scalars().all()

    if critical_changes:
        _send_critical_alert(project, owner, critical_changes)
        sent_count += 1

    # 3. Send daily digest email
    if analysis:
        _send_daily_digest(project, owner, analysis)
        sent_count += 1

    return sent_count


def _send_daily_digest(project: Project, owner: User, analysis: dict):
    """Send daily digest email via Resend."""
    summary = analysis.get("summary", "No significant changes today.")
    severity = analysis.get("severity", "low")
    insights = analysis.get("insights", [])
    recommendations = analysis.get("recommendations", [])

    # Build HTML email
    insights_html = ""
    for insight in insights[:5]:
        impact_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(
            insight.get("impact", "low"), "#8b8b96"
        )
        insights_html += f"""
        <div style="padding:12px;margin:8px 0;background:#f9fafb;border-radius:8px;border-left:3px solid {impact_color}">
            <strong>{insight.get('title', '')}</strong><br>
            <span style="color:#666;font-size:14px">{insight.get('description', '')}</span>
        </div>"""

    recs_html = ""
    for rec in recommendations[:3]:
        recs_html += f"""
        <div style="padding:12px;margin:8px 0;background:#f0fdf4;border-radius:8px">
            <strong>#{rec.get('priority', '')}: {rec.get('action', '')}</strong><br>
            <span style="color:#666;font-size:14px">{rec.get('reason', '')}</span>
        </div>"""

    severity_badge = {
        "low": "🟢 Low", "medium": "🟡 Medium",
        "high": "🟠 High", "critical": "🔴 Critical",
    }.get(severity, "⚪ Unknown")

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#111">📊 Daily SEO Report — {project.domain}</h2>
        <p style="color:#666;font-size:14px">{date.today().strftime('%B %d, %Y')} · Severity: {severity_badge}</p>
        <div style="padding:16px;background:#f8fafc;border-radius:12px;margin:16px 0">
            <p style="font-size:15px;color:#333">{summary}</p>
        </div>
        {"<h3>🔍 Key Insights</h3>" + insights_html if insights_html else ""}
        {"<h3>✅ Recommendations</h3>" + recs_html if recs_html else ""}
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
        <p style="color:#999;font-size:12px">SEO Competitor Tracker · <a href="#">View full report</a></p>
    </div>
    """

    _send_email(
        to=owner.email,
        subject=f"[{severity_badge}] {project.domain} — Daily SEO Digest",
        html=html,
    )


def _send_critical_alert(project: Project, owner: User, changes: list):
    """Send instant alert for critical rank changes."""
    changes_text = ""
    for rh in changes[:10]:
        direction = "📈" if rh.position_change > 0 else "📉"
        kw_text = rh.keyword.keyword if rh.keyword else "?"
        changes_text += f"""
        <div style="padding:8px 12px;margin:4px 0;background:#fef2f2;border-radius:6px">
            {direction} <strong>{kw_text}</strong>: position {rh.position or '100+'} 
            ({'+' if rh.position_change > 0 else ''}{rh.position_change}) · {rh.domain}
        </div>"""

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#ef4444">🚨 Critical Rank Alert — {project.domain}</h2>
        <p style="color:#666">Significant position changes detected ({len(changes)} keywords)</p>
        {changes_text}
        <p style="margin-top:16px"><a href="#" style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none">View Details</a></p>
    </div>
    """

    _send_email(
        to=owner.email,
        subject=f"🚨 Critical: {len(changes)} major rank changes on {project.domain}",
        html=html,
    )


def _send_email(to: str, subject: str, html: str):
    """Send email via Resend API."""
    if not settings.resend_api_key:
        logger.warning("Resend API key not set, skipping email", to=to)
        return

    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": "SEO Tracker <noreply@yourdomain.com>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent", to=to, subject=subject)
    except Exception as e:
        logger.error("Email send failed", to=to, error=str(e))
