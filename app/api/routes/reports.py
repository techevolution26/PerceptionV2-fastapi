from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models.models import AdminAuditLog, Perception, PerceptionReport, User
from app.core.config import get_settings
from app.services.rate_limiter import enforce_rate_limit
from app.schemas.report import (
    CreatePerceptionReportRequest,
    PerceptionReportOut,
    PerceptionReportStatus,
    UpdatePerceptionReportRequest,
)

router = APIRouter(tags=["reports"])
settings = get_settings()


@router.post(
    "/perceptions/{perception_id}/reports",
    response_model=PerceptionReportOut,
    status_code=status.HTTP_201_CREATED,
)
async def report_perception(
    perception_id: int,
    payload: CreatePerceptionReportRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    await enforce_rate_limit(
        scope="report-create-10m",
        identity=f"user:{current_user.id}",
        limit=settings.REPORT_RATE_LIMIT_PER_10_MINUTES,
        window_seconds=600,
        message="You have submitted several reports recently. Please try again later.",
    )

    perception = await db.scalar(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .where(Perception.id == perception_id, User.is_active.is_(True))
    )
    if perception is None:
        raise HTTPException(404, "Perception not found")

    if perception.user_id == current_user.id:
        raise HTTPException(400, "You cannot report your own perception.")

    existing = await db.scalar(
        select(PerceptionReport).where(
            PerceptionReport.reporter_user_id == current_user.id,
            PerceptionReport.perception_id == perception_id,
        )
    )
    if existing is not None:
        raise HTTPException(409, "You have already reported this perception.")

    report = PerceptionReport(
        reporter_user_id=current_user.id,
        perception_id=perception_id,
        reason=payload.reason.value,
        details=payload.details.strip() if payload.details else None,
        status=PerceptionReportStatus.PENDING.value,
    )
    db.add(report)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "You have already reported this perception.")
    await db.refresh(report)
    return report


@router.get("/admin/reports", response_model=list[PerceptionReportOut])
async def list_reports(
    admin: AdminUser,
    db: DbSession,
    report_status: PerceptionReportStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
):
    stmt = (
        select(PerceptionReport)
        .order_by(PerceptionReport.created_at.desc(), PerceptionReport.id.desc())
        .limit(limit)
    )
    if report_status is not None:
        stmt = stmt.where(PerceptionReport.status == report_status.value)
    reports = (await db.execute(stmt)).scalars().all()
    return reports


@router.patch("/admin/reports/{report_id}", response_model=PerceptionReportOut)
async def update_report(
    report_id: int,
    payload: UpdatePerceptionReportRequest,
    admin: AdminUser,
    db: DbSession,
):
    report = await db.scalar(
        select(PerceptionReport).where(PerceptionReport.id == report_id)
    )
    if report is None:
        raise HTTPException(404, "Report not found")

    if report.status != PerceptionReportStatus.PENDING.value:
        raise HTTPException(409, "This report has already been resolved.")
    if payload.status == PerceptionReportStatus.PENDING:
        raise HTTPException(400, "A report must be resolved to reviewed, actioned, or dismissed.")

    report.status = payload.status.value
    report.resolution_note = payload.resolution_note.strip() if payload.resolution_note else None
    report.reviewed_by_user_id = admin.id
    report.reviewed_at = datetime.now(timezone.utc)
    db.add(
        AdminAuditLog(
            actor_user_id=admin.id,
            action="perception.report.resolved",
            data={
                "report_id": report.id,
                "perception_id": report.perception_id,
                "status": report.status,
            },
        )
    )
    await db.commit()
    await db.refresh(report)
    return report
