# Third-Party AI Data Processing Boundary

Perception's comment-intelligence worker is an optional external processing path.

## Default

```text
COMMENT_INTELLIGENCE_ENABLED=false
COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED=false
```

Both controls are required because a feature flag alone is not enough to establish an explicit privacy decision.

## Data sent

Only:

- topic name
- perception text
- comment text

The request deliberately excludes:

- user ID
- commenter name
- email
- profession
- country
- region
- city
- verification data
- subscription data
- account metadata

## Data retained locally

Perception stores normalized semantic results in `CommentIntelligence` rather than provider request payloads.

## Provider controls

The implementation sends `store=false` and does not use provider responses as a source of participant identity.

The production privacy review must still account for the provider's current retention/abuse-monitoring terms. `store=false` must not be described to users as a guarantee of zero retention.

## Operational rule

If external processing is not explicitly allowed, the worker must not make provider requests. Pending analysis remains pending until the privacy gate is intentionally enabled.
