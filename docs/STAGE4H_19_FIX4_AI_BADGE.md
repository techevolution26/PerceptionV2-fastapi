# Stage 4H.19 FIX4 — AI Badge Visibility

## Purpose
Restore the owner-only AI response badge on the Perception comment tree without changing the existing badge design.

## Root cause
The comments endpoint used a SQLAlchemy `User` alias named `owner` for the SQL join, then incorrectly reused that alias in Python when checking whether the authenticated viewer owned the perception. The Python authorization check therefore did not compare the viewer to the real perception owner's user ID.

The replies endpoint also lacked the authenticated optional viewer context while attempting to use the same AI-status visibility flag.

## Fix
- Resolve the actual `Perception.user_id` before deciding whether AI response status may be exposed.
- Require the authenticated viewer to be the perception owner.
- Require an active subscription whose plan has `analytics_enabled`.
- Apply the same rule to `/api/comments/{comment_id}/replies`.
- Keep `ai_analysis_status` null for viewers who do not satisfy the owner + analytics entitlement rule.
- Keep the existing mobile `AIAnalysisBadge` component and wording unchanged.
- Restore the badge to the far-right side of the comment/reply header row.

## Expected behavior
1. Owner + active analytics subscription + Profile → Posts → Perception: badge appears on analyzed/pending/failed comments and replies at the far right.
2. Owner without analytics subscription: no badge/status.
3. Non-owner: no badge/status.
4. Owner subscribed but opens the perception outside the Profile → Posts route: detail-screen authorization still prevents the badge unless `aiAnalysis=1` is explicitly carried from the approved profile flow.

## Database
No migration required.
