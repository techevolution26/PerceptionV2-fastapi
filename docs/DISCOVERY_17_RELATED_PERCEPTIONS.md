# Discovery 17 — Related Perceptions

Related Perceptions are contextual, not popularity-based. Candidate ordering uses the source Topic, qualifying stored conversation themes, professional lens, observed sentiment/stance context, and bounded recency.

Semantic relationship is only used when both source and candidate have at least five analyzed comments. Raw comment text is never returned or used as a request-path LLM prompt. Likes, comments count, views, follower count, and engagement rate are not ranking inputs.

The endpoint is `GET /api/perceptions/{perception_id}/related` and returns existing `PerceptionOut` cards plus an explainable reason. No participant identity or city-level intelligence is exposed.
