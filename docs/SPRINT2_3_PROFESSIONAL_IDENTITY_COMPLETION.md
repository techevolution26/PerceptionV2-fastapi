# Sprint 2.3 — Professional Identity Completion

## Objective
Make structured professional identity a coherent, reusable product signal without conflating professional identity with verification.

## Contract
- A professional identity consists of one or more industries, one or more professional roles, and one primary professional role.
- A selected role belongs to its taxonomy mother industry; the client keeps that relationship coherent.
- The primary professional role is the leading identity displayed on profile/perception surfaces.
- A professional badge represents selected professional identity.
- A verification badge is separate and appears only when the account is `VERIFIED` and has at least one `verified_professional_roles` entry.
- Verification is never inferred from selecting a role, industry, subscription, or onboarding completion.
- Public profile serialization exposes the structured professional identity fields required by the mobile badge/profile surfaces.

## Completion flow
`Industry → Professional role(s) → Primary professional focus → Save → Verification (optional/separate)`

## Acceptance
- Users cannot save an incomplete professional identity from the completion screen.
- Removing an industry removes roles belonging exclusively to that industry and reassigns the primary role when necessary.
- Selecting a role automatically includes its taxonomy mother industry.
- Existing professional identity data remains compatible.
- No new verification state is created by this sprint.
