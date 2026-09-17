# Conversation-First Product Guardrails

Perception is designed around organized, useful conversations rather than an information-dense social feed.

## Home

- The Topic carousel remains the chief display at the top of Home.
- Authenticated Home presents a compact `For you / Recommendations` navigation row rather than a large recommendation panel.
- `For you` remains the primary feed view.
- Recommendations are available as a deliberate destination instead of competing with the feed for attention.
- Do not add additional discovery rails to Home merely because data is available.

## Perception detail

Related Perceptions are an intentional, user-controlled secondary exploration layer.

They are not shown by default.

The Related Perceptions control becomes available only when both conditions are met during the current detail-screen visit:

1. The user has remained continuously on the same Perception for at least two minutes.
2. The user has demonstrated meaningful interaction by liking, saving, commenting, or replying.

The user then chooses whether to turn Related Perceptions on. Turning it off hides the secondary layer. The related endpoint is not requested until the user opts in.

Leaving the detail screen cancels the dwell timer. Background time does not qualify as sustained interest.

## Recommendations

Recommendation perception cards use the same canonical like/save/report actions as the rest of the product. Recommendation placement does not create a separate interaction implementation.

## Discovery principle

Discovery should support conversation, not overwhelm it:

`Topic → Perception → Response → Conversation → Contextual discovery`

Popularity is not a substitute for contextual relevance, and every secondary discovery surface should earn its place through user intent or demonstrated interest.
