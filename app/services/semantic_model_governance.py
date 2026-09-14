"""Governance checks for semantic model-version changes."""

from __future__ import annotations
from collections import Counter

MINIMUM_VERSION_SAMPLE = 5
DISTRIBUTION_SHIFT_THRESHOLD = 0.20


def _dist(rows, field):
    c = Counter(getattr(r, field) for r in rows if getattr(r, field))
    t = sum(c.values())
    return {k: v / t for k, v in c.items()} if t else {}


def _max_shift(a, b):
    return max((abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b)), default=0.0)


def assess_semantic_model_governance(
    rows, *, minimum_version_sample: int = MINIMUM_VERSION_SAMPLE
) -> dict:
    versions = Counter(str(r.model_version) for r in rows if r.model_version)
    ordered = [v for v, _ in versions.most_common()]
    active = [{"model_version": v, "comments": c} for v, c in versions.most_common()]
    if len(ordered) <= 1:
        return {
            "status": "stable",
            "active_model_versions": active,
            "baseline_model_version": ordered[0] if ordered else None,
            "latest_model_version": ordered[0] if ordered else None,
            "compared_sample_size": 0,
            "distribution_shifts": [],
            "note": (
                "A single semantic model version is present in the qualifying sample; no version comparison is required."
                if ordered
                else "No model version is available in the qualifying sample."
            ),
            "limitations": [
                "Model-version stability does not establish semantic truth or representativeness."
            ],
        }
    latest = str(
        max(
            (r for r in rows if r.model_version),
            key=lambda r: r.analyzed_at or r.created_at,
        ).model_version
    )
    baseline = next(v for v in ordered if v != latest)
    lr = [r for r in rows if r.model_version == latest]
    br = [r for r in rows if r.model_version == baseline]
    if len(lr) < minimum_version_sample or len(br) < minimum_version_sample:
        return {
            "status": "insufficient_sample",
            "active_model_versions": active,
            "baseline_model_version": baseline,
            "latest_model_version": latest,
            "compared_sample_size": min(len(lr), len(br)),
            "distribution_shifts": [],
            "note": f"Version comparison is withheld until both compared model versions have at least {minimum_version_sample} analyzed comments.",
            "limitations": [
                "Small version-specific samples cannot support a defensible comparison."
            ],
        }
    shifts = []
    for field in ("sentiment", "stance"):
        x = round(_max_shift(_dist(br, field), _dist(lr, field)), 3)
        shifts.append(
            {
                "dimension": field,
                "max_distribution_shift": x,
                "review_required": x >= DISTRIBUTION_SHIFT_THRESHOLD,
            }
        )
    bt = Counter(t for r in br for t in (r.themes or []))
    lt = Counter(t for r in lr for t in (r.themes or []))
    bs = {x for x, _ in bt.most_common(5)}
    ls = {x for x, _ in lt.most_common(5)}
    overlap = len(bs & ls) / max(1, len(bs | ls))
    shifts.append(
        {
            "dimension": "top_themes",
            "top_theme_overlap": round(overlap, 3),
            "review_required": overlap < 0.5,
        }
    )
    return {
        "status": (
            "review_required"
            if any(x.get("review_required") for x in shifts)
            else "stable"
        ),
        "active_model_versions": active,
        "baseline_model_version": baseline,
        "latest_model_version": latest,
        "compared_sample_size": min(len(lr), len(br)),
        "distribution_shifts": shifts,
        "note": "Version comparison describes observed output differences; it does not prove that either model version is more truthful.",
        "limitations": [
            "Semantic output can change because of model version, data composition, or other analysis conditions.",
            "Distribution shifts are governance signals for review, not causal findings.",
        ],
    }
