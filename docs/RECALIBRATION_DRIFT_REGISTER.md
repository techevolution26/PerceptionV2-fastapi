# Perception Recalibration — Drift Register

## Purpose

This register records implementation/product drift discovered while reconciling the current recalibration packages with the frozen Perception Intelligence foundation.

The rule is simple:

> Fix drift at the smallest responsible layer without reopening stable intelligence contracts.

## Drift 01 — User verification status vocabulary

### Symptom

The mobile UI correctly treats `VERIFIED` as the canonical user verification state, but the demo seeder had been creating verified users with:

`verification_status = "APPROVED"`

`APPROVED` is the correct status for a **VerificationApplication**, not for the persisted user's verification state.

### Impact

A genuinely approved/verified professional could fail the frontend condition:

`verification_status === "VERIFIED" && verified_professional_roles.length > 0`

and therefore lose the professional verification badge.

### Correction

- Demo users now use `VERIFIED`.
- Verification applications continue to use `APPROVED`.
- Migration `0014_normalize_user_verification_status` converts existing user rows with `APPROVED` to `VERIFIED`.
- The mobile badge remains based on the canonical user contract.

### Invariant

```text
VerificationApplication.status
    APPROVED / REJECTED / PENDING

User.verification_status
    VERIFIED / REJECTED / PENDING / NOT_APPLIED
```

These are intentionally different state machines.

## Drift 02 — AI badge authorization

Previously resolved in 4H.19 FIX4.

The comments route was incorrectly using a SQLAlchemy `User` alias as though it were the actual perception owner instance.

Correction:

- resolve actual `Perception.user_id`;
- compare against authenticated viewer;
- require analytics entitlement;
- apply the same rule to replies;
- keep unauthorized `ai_analysis_status` null.

The visual badge remains at the far right of the comment/reply header.

## Drift-control rules

1. Do not change a canonical enum/value to satisfy a UI condition without tracing its owning domain.
2. Distinguish application state from user state.
3. Backend response contracts remain authoritative.
4. Frontend flags are presentation controls, never security boundaries.
5. New intelligence features must consume the frozen 4H evidence contracts.
6. A bug fix must not silently alter Topic, Perception, Response, Lens, Evidence, Provenance, Quality, Freshness, or Governance semantics.
7. Every discovered drift should be recorded before the next major capability begins.
