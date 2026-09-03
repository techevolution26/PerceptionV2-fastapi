from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import BillingEvent, Plan, Subscription, User


def _dt_from_unix(value: Any) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _status_for_access(status: str, current_period_end: datetime | None) -> bool:
    if status in {"active", "trialing"}:
        return True
    if status == "past_due" and current_period_end is not None:
        return current_period_end > datetime.now(timezone.utc)
    return False


async def sync_stripe_subscription(db: AsyncSession, stripe_subscription: dict[str, Any]) -> Subscription | None:
    metadata = stripe_subscription.get("metadata") or {}
    user_id_raw = metadata.get("user_id")
    plan_code = metadata.get("plan_code")
    stripe_subscription_id = stripe_subscription.get("id")
    if not stripe_subscription_id:
        return None

    sub_result = await db.execute(
        select(Subscription)
        .where(Subscription.provider == "stripe", Subscription.provider_subscription_id == stripe_subscription_id)
        .options(selectinload(Subscription.plan))
    )
    sub = sub_result.scalar_one_or_none()

    if sub is None and user_id_raw is not None:
        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            user_id = None
        if user_id is not None:
            sub_result = await db.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id, Subscription.provider == "stripe")
                .order_by(Subscription.starts_at.desc())
                .options(selectinload(Subscription.plan))
            )
            sub = sub_result.scalars().first()

    if sub is None or plan_code:
        plan = None
        if plan_code:
            plan_result = await db.execute(select(Plan).where(Plan.code == plan_code))
            plan = plan_result.scalar_one_or_none()
        if sub is None and user_id_raw is not None and plan is not None:
            sub = Subscription(
                user_id=int(user_id_raw),
                plan_id=plan.id,
                provider="stripe",
                provider_subscription_id=str(stripe_subscription_id),
                provider_customer_id=str(stripe_subscription.get("customer")) if stripe_subscription.get("customer") else None,
                starts_at=_dt_from_unix(stripe_subscription.get("start_date")) or datetime.now(timezone.utc),
            )
            db.add(sub)
        elif sub is not None and plan is not None:
            sub.plan_id = plan.id

    if sub is None:
        return None

    sub.status = str(stripe_subscription.get("status") or "unknown")
    sub.provider = "stripe"
    if stripe_subscription.get("customer"):
        sub.provider_customer_id = str(stripe_subscription["customer"])
    sub.provider_subscription_id = str(stripe_subscription_id)
    sub.current_period_start = _dt_from_unix(stripe_subscription.get("current_period_start"))
    sub.current_period_end = _dt_from_unix(stripe_subscription.get("current_period_end"))
    sub.trial_ends_at = _dt_from_unix(stripe_subscription.get("trial_end"))
    sub.cancel_at_period_end = bool(stripe_subscription.get("cancel_at_period_end", False))
    sub.canceled_at = _dt_from_unix(stripe_subscription.get("canceled_at"))
    sub.ends_at = sub.current_period_end if sub.cancel_at_period_end else None
    return sub


async def process_stripe_event(db: AsyncSession, event: dict[str, Any]) -> bool:
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    if not event_id or not event_type:
        return False

    statement = (
        insert(BillingEvent)
        .values(
            provider="stripe",
            provider_event_id=event_id,
            event_type=event_type,
            payload=event,
        )
        .on_conflict_do_nothing(index_elements=["provider", "provider_event_id"])
    )
    inserted = await db.execute(statement)
    if inserted.rowcount != 1:
        return False

    obj = ((event.get("data") or {}).get("object") or {})
    if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        await sync_stripe_subscription(db, obj)
    elif event_type == "checkout.session.completed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            # The Checkout Session includes only the ID; the next subscription webhook
            # carries the authoritative subscription state. This event is still recorded
            # for audit/idempotency.
            pass
    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.provider == "stripe",
                    Subscription.provider_subscription_id == str(subscription_id),
                )
            )
            sub = result.scalar_one_or_none()
            if sub is not None and sub.status == "active":
                sub.status = "past_due"
    elif event_type == "invoice.paid":
        subscription_id = obj.get("subscription")
        if subscription_id:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.provider == "stripe",
                    Subscription.provider_subscription_id == str(subscription_id),
                )
            )
            sub = result.scalar_one_or_none()
            if sub is not None and sub.status == "past_due":
                sub.status = "active"

    event_result = await db.execute(
        select(BillingEvent).where(BillingEvent.provider == "stripe", BillingEvent.provider_event_id == event_id)
    )
    billing_event = event_result.scalar_one()
    billing_event.processed_at = datetime.now(timezone.utc)
    await db.commit()
    return True


def has_analytics_access(sub: Subscription | None) -> bool:
    if sub is None or sub.plan is None:
        return False
    return bool(sub.plan.analytics_enabled and _status_for_access(sub.status, sub.current_period_end or sub.ends_at or sub.trial_ends_at))
