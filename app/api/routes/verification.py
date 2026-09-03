from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models.models import AnalyticsTopic, Topic, User, VerificationApplication
from app.schemas.verification import VerificationApplicationCreate, VerificationApplicationOut
from app.services.subscriptions import require_analytics_access

router = APIRouter(prefix="/verification", tags=["verification"])


def badge_for(profession: str, focus: str, topic_name: str | None) -> str:
    text = f"{profession} {focus} {topic_name or ''}".lower()
    if "science" in text or "research" in text or "biology" in text or "chem" in text:
        return "🔬"
    if "math" in text or "statistics" in text:
        return "∑"
    if "business" in text or "finance" in text or "econom" in text:
        return "📈"
    if "education" in text or "teacher" in text or "academic" in text:
        return "🎓"
    if "technology" in text or "software" in text or "engineer" in text:
        return "⌘"
    if "health" in text or "medical" in text:
        return "⚕"
    return "✦"


@router.get("/me", response_model=VerificationApplicationOut | None)
async def get_my_application(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(VerificationApplication)
        .where(VerificationApplication.user_id == current_user.id)
        .order_by(VerificationApplication.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/applications", response_model=VerificationApplicationOut, status_code=status.HTTP_201_CREATED)
async def apply(
    payload: VerificationApplicationCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    sub = await require_analytics_access(db, current_user.id)
    if not sub.plan.verification_included:
        raise HTTPException(status_code=403, detail="Your plan does not include professional verification.")

    if current_user.verification_status in {"PENDING", "VERIFIED"}:
        raise HTTPException(status_code=409, detail="You already have an active verification application.")

    topic_ids = list(dict.fromkeys(payload.requested_topic_ids))
    if payload.primary_topic_id is not None and payload.primary_topic_id not in topic_ids:
        topic_ids.insert(0, payload.primary_topic_id)

    if len(topic_ids) > sub.plan.max_topics:
        raise HTTPException(
            status_code=422,
            detail=f"Your plan supports up to {sub.plan.max_topics} analytics topics.",
        )

    if topic_ids:
        count = (
            await db.execute(select(Topic.id).where(Topic.id.in_(topic_ids)))
        ).scalars().all()
        if len(count) != len(topic_ids):
            raise HTTPException(status_code=422, detail="One or more requested topics are invalid.")

    primary_name = None
    if payload.primary_topic_id is not None:
        primary_name = (
            await db.execute(select(Topic.name).where(Topic.id == payload.primary_topic_id))
        ).scalar_one_or_none()

    badge = badge_for(payload.profession, payload.focus, primary_name)

    current_user.profession = payload.profession
    current_user.professional_focus = payload.focus
    current_user.primary_analytics_topic_id = payload.primary_topic_id
    current_user.analytics_specialties = topic_ids
    current_user.verification_status = "PENDING"

    db.add(
        VerificationApplication(
            user_id=current_user.id,
            profession=payload.profession,
            focus=payload.focus,
            primary_topic_id=payload.primary_topic_id,
            requested_topic_ids=topic_ids,
            evidence=payload.evidence,
            status="PENDING",
            badge=badge,
        )
    )
    await db.commit()

    result = await db.execute(
        select(VerificationApplication)
        .where(VerificationApplication.user_id == current_user.id)
        .order_by(VerificationApplication.created_at.desc())
        .limit(1)
    )
    return result.scalar_one()


@router.get("/admin/applications", response_model=list[VerificationApplicationOut])
async def admin_list_applications(admin: AdminUser, db: DbSession):
    result = await db.execute(
        select(VerificationApplication)
        .order_by(VerificationApplication.created_at.desc())
    )
    return result.scalars().all()


@router.post("/admin/applications/{application_id}/review", response_model=VerificationApplicationOut)
async def admin_review_application(
    application_id: int,
    approved: bool,
    reviewer_note: str | None,
    admin: AdminUser,
    db: DbSession,
):
    result = await db.execute(
        select(VerificationApplication).where(VerificationApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=404, detail="Verification application not found")

    user_result = await db.execute(select(User).where(User.id == application.user_id))
    user = user_result.scalar_one()

    application.status = "APPROVED" if approved else "REJECTED"
    application.reviewer_note = reviewer_note
    user.verification_status = "VERIFIED" if approved else "REJECTED"
    if approved:
        user.verification_badge = application.badge
    elif user.verification_badge:
        user.verification_badge = None

    await db.commit()
    return application
