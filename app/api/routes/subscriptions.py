from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.models import Plan, Subscription
from app.schemas.business import (
    BillingInvoiceOut,
    BillingPortalOut,
    CheckoutOut,
    PlanOut,
    SubscriptionOut,
    TrialRequest,
)
from app.services.billing import BillingProviderError, StripeBillingProvider
from app.services.billing_sync import process_stripe_event
from app.services.subscriptions import get_current_subscription, get_plan

router = APIRouter(prefix="/subscription", tags=["subscriptions"])


def _to_out(sub: Subscription | None) -> SubscriptionOut:
    if sub is None:
        return SubscriptionOut(status="NONE")
    plan = sub.plan
    now = datetime.now(timezone.utc)
    expiry = sub.current_period_end or sub.ends_at or sub.trial_ends_at
    active = sub.status in {"ACTIVE", "TRIALING", "active", "trialing", "past_due"} and (
        expiry is None or expiry > now
    )
    return SubscriptionOut(
        id=sub.id,
        status=sub.status.upper() if active else "EXPIRED",
        plan=plan,
        starts_at=sub.starts_at,
        ends_at=sub.ends_at,
        trial_ends_at=sub.trial_ends_at,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        analytics_enabled=bool(active and plan and plan.analytics_enabled),
        max_topics=plan.max_topics if active and plan else 0,
        verification_included=bool(active and plan and plan.verification_included),
    )


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: DbSession):
    result = await db.execute(select(Plan).where(Plan.active.is_(True)).order_by(Plan.price_cents))
    return result.scalars().all()


@router.get("", response_model=SubscriptionOut)
async def current_subscription(current_user: CurrentUser, db: DbSession):
    return _to_out(await get_current_subscription(db, current_user.id))


async def _create_checkout(plan: Plan, current_user, db) -> CheckoutOut:
    if plan.price_cents <= 0:
        raise HTTPException(status_code=422, detail="The free plan does not require checkout.")
    if not plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="This plan is not configured for Stripe checkout yet.",
        )

    existing = await get_current_subscription(db, current_user.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already have an active subscription or trial.")

    provider = StripeBillingProvider()
    customer_id = current_user.billing_customer_id
    try:
        if not customer_id:
            customer_id = await provider.create_customer(
                email=current_user.email,
                name=current_user.name,
                user_id=current_user.id,
            )
            current_user.billing_customer_id = customer_id
            await db.flush()

        checkout = await provider.create_checkout_session(
            customer_id=customer_id,
            price_id=plan.stripe_price_id,
            plan_code=plan.code,
            user_id=current_user.id,
            trial_days=plan.trial_days,
        )
    except BillingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CheckoutOut(
        plan=plan,
        checkout_url=checkout.url,
        checkout_session_id=checkout.id,
        trial_days=plan.trial_days,
        message=(
            f"Your {plan.trial_days}-day trial will begin after Stripe Checkout is completed."
            if plan.trial_days > 0
            else "Complete Stripe Checkout to activate analytics."
        ),
    )


@router.post("/trial", response_model=CheckoutOut)
async def start_trial(payload: TrialRequest, current_user: CurrentUser, db: DbSession):
    plan = await get_plan(db, payload.plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.trial_days <= 0:
        raise HTTPException(status_code=422, detail="This plan does not offer a trial.")
    return await _create_checkout(plan, current_user, db)


@router.post("/checkout", response_model=CheckoutOut)
async def checkout(payload: TrialRequest, current_user: CurrentUser, db: DbSession):
    plan = await get_plan(db, payload.plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return await _create_checkout(plan, current_user, db)


@router.post("/portal", response_model=BillingPortalOut)
async def billing_portal(current_user: CurrentUser, db: DbSession):
    if not current_user.billing_customer_id:
        raise HTTPException(status_code=404, detail="No billing customer exists yet.")
    try:
        url = await StripeBillingProvider().create_portal_session(customer_id=current_user.billing_customer_id)
    except BillingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return BillingPortalOut(portal_url=url)


@router.get("/invoices", response_model=list[BillingInvoiceOut])
async def billing_invoices(current_user: CurrentUser):
    if not current_user.billing_customer_id:
        return []
    try:
        invoices = await StripeBillingProvider().list_invoices(customer_id=current_user.billing_customer_id)
    except BillingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        BillingInvoiceOut(
            id=str(invoice["id"]),
            number=invoice.get("number"),
            status=invoice.get("status"),
            currency=invoice.get("currency"),
            amount_due=int(invoice.get("amount_due") or 0),
            amount_paid=int(invoice.get("amount_paid") or 0),
            hosted_invoice_url=invoice.get("hosted_invoice_url"),
            invoice_pdf=invoice.get("invoice_pdf"),
            created_at=datetime.fromtimestamp(int(invoice["created"]), tz=timezone.utc) if invoice.get("created") else None,
            period_start=datetime.fromtimestamp(int(invoice["period_start"]), tz=timezone.utc) if invoice.get("period_start") else None,
            period_end=datetime.fromtimestamp(int(invoice["period_end"]), tz=timezone.utc) if invoice.get("period_end") else None,
        )
        for invoice in invoices
    ]


@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(current_user: CurrentUser, db: DbSession):
    sub = await get_current_subscription(db, current_user.id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription")
    if sub.provider != "stripe" or not sub.provider_subscription_id:
        raise HTTPException(status_code=409, detail="This subscription cannot be canceled through Stripe.")
    # Cancellation is deliberately delegated to the Stripe Customer Portal.
    raise HTTPException(status_code=409, detail="Manage cancellation from the billing portal.")


@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: DbSession):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    provider = StripeBillingProvider()
    try:
        event = provider.verify_webhook(payload, signature, provider.webhook_secret)
        processed = await process_stripe_event(db, event)
    except BillingProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True, "processed": processed}
