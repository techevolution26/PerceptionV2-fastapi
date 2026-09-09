from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import Plan, Subscription


def subscription_has_current_access(sub: Subscription | None, now: datetime | None = None) -> bool:
    """Return whether a subscription is currently entitled to its plan.

    ``past_due`` is a temporary grace state only while the current paid period
    remains valid. Missing or expired period boundaries fail closed.
    """
    if sub is None or sub.plan is None:
        return False
    now = now or datetime.now(timezone.utc)
    status = sub.status.lower()
    expiry = sub.current_period_end or sub.ends_at or sub.trial_ends_at
    if expiry is not None and expiry <= now:
        return False
    if status in {"active", "trialing"}:
        return True
    return status == "past_due" and expiry is not None and expiry > now


async def get_current_subscription(db, user_id: int) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .options(selectinload(Subscription.plan))
        .order_by(Subscription.starts_at.desc())
    )
    subscriptions = result.scalars().all()
    now = datetime.now(timezone.utc)
    for sub in subscriptions:
        if subscription_has_current_access(sub, now):
            return sub
        if sub.status.lower() in {"active", "trialing", "past_due"}:
            expiry = sub.current_period_end or sub.ends_at or sub.trial_ends_at
            if expiry is not None and expiry <= now:
                sub.status = "EXPIRED"
    if subscriptions:
        await db.flush()
    return None


async def require_analytics_access(db, user_id: int) -> Subscription:
    sub = await get_current_subscription(db, user_id)
    if sub is None or not sub.plan.analytics_enabled:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "ANALYTICS_SUBSCRIPTION_REQUIRED",
                "message": "An active analytics subscription is required.",
            },
        )
    return sub


async def get_plan(db, code: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.code == code, Plan.active.is_(True)))
    return result.scalar_one_or_none()
