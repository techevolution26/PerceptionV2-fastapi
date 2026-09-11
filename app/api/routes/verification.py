from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.api.deps import CurrentUser, DbSession, SuperAdminUser
from app.models.models import AdminAuditLog, User, VerificationApplication
from app.schemas.verification import VerificationApplicationCreate, VerificationApplicationOut
from app.services.subscriptions import require_analytics_access
from app.services.professional_taxonomy import ROLE_MAP, validate_identity_selection

router = APIRouter(prefix="/verification", tags=["verification"])



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

    industry_codes = list(dict.fromkeys(payload.industry_codes))
    role_codes = list(dict.fromkeys(payload.professional_role_codes))
    try:
        validate_identity_selection(industry_codes, role_codes, payload.primary_professional_role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not role_codes:
        raise HTTPException(status_code=422, detail="Select at least one professional role before applying for verification.")

    # Verification is a professional-identity review. Analytics topic scope
    # belongs to /user/analytics-profile and must never be changed as a side
    # effect of a verification application. Keep the legacy request fields in
    # the schema for compatibility, but reject their use explicitly.
    if payload.primary_topic_id is not None or payload.requested_topic_ids:
        raise HTTPException(
            status_code=422,
            detail="Analytics topics are managed separately from professional verification.",
        )

    primary_role = payload.primary_professional_role or role_codes[0]
    badge = ROLE_MAP[primary_role]["icon"]

    current_user.profession = payload.profession
    current_user.professional_focus = payload.focus
    current_user.professional_industries = industry_codes
    current_user.professional_roles = role_codes
    current_user.primary_professional_role = primary_role
    current_user.verification_status = "PENDING"

    db.add(
        VerificationApplication(
            user_id=current_user.id,
            profession=payload.profession,
            industry_codes=industry_codes,
            professional_role_codes=role_codes,
            primary_professional_role=primary_role,
            focus=payload.focus,
            primary_topic_id=None,
            requested_topic_ids=[],
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
async def admin_list_applications(admin: SuperAdminUser, db: DbSession):
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
    admin: SuperAdminUser,
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
    user.verified_professional_roles = list(application.professional_role_codes) if approved else []
    db.add(AdminAuditLog(
        actor_user_id=admin.id,
        target_user_id=user.id,
        action="professional_verification.approved" if approved else "professional_verification.rejected",
        data={"application_id": application.id, "roles": application.professional_role_codes, "industries": application.industry_codes},
    ))
    if approved:
        user.verification_badge = application.badge
    elif user.verification_badge:
        user.verification_badge = None

    await db.commit()
    return application
