# Discovery 15 — Feed Ranking

## Objective
Move from search refinement to a viewer-specific feed: rank a bounded recent candidate pool according to explicit user context and behavior without turning popularity into the ranking objective.

## Ranking inputs
- Followed topics
- Followed creators
- Topics explicitly interacted with through likes, saves, and comments
- Primary professional role
- Primary professional industry
- Public country/region context only
- Recency

## Explicit exclusions
Global likes, comments, views, followers, and engagement rate are not ranking inputs.
Private geography and city-level geography are not ranking inputs.

## Diversity
After relevance scoring, the feed limits one creator to three selected items and one topic to four selected items before filling remaining slots from deferred candidates. This prevents one source from monopolizing the feed without replacing relevance with popularity.

## Product boundary
Personalization answers: "what may be relevant to this person?"
Intelligence answers: "what patterns/signals/evidence exist?"
Decision intelligence answers: "what does that evidence mean for a decision?"
