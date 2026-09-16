# Discovery 18 — Related Topics

## Objective

Make topic discovery contextual to the topic currently being viewed. Related topics are derived from the existing Topic → Perception graph, with qualified conversation themes and professional context as additional signals. Personalization may rerank a relationship, but popularity is not a relationship signal.

## Contract

`GET /api/topics/{topic_id}/related`

Returns up to 5 explainable related topics, bounded to 10 by the service.

## Relationship signals

- Shared contributors across both topics, without exposing contributor identity.
- Shared conversation themes only when each topic has at least 5 analyzed comments from at least 5 distinct commenters.
- Overlapping professional roles among active contributors.
- Viewer topic affinity from explicit follows/interactions.
- Recency as a small freshness tie-breaker.

## Excluded signals

- Follower count as a ranking signal.
- Likes, comments, views, engagement rate, or global popularity.
- City or GPS location.
- Individual participant identity in the response.
- LLM/provider calls in the request path.

## Product distinction

Recommendations answer: “What might this person want to explore?”

Related topics answer: “What topics are contextually connected to the topic I am viewing?”
