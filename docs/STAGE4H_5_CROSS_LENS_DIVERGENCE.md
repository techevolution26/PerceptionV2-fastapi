# Stage 4H.5 — Cross-Lens Divergence & Convergence

## Purpose

Stage 4H.5 compares qualifying professional and geographic cohorts for descriptive alignment and difference. It does not infer causes, motivations, predictions, population-wide opinion, or individual attributes.

## Rules

- A cohort must meet the existing minimum sample of 5 analyzed comments.
- No individual participant identity is returned.
- City-level reporting remains excluded.
- **Convergence** requires the same leading stance and at least one shared theme among the leading recorded themes.
- **Stance divergence** is reported when qualifying cohorts have different leading stances.
- **Thematic divergence** is reported when qualifying cohorts share a leading stance but have no overlapping leading themes.
- Comparisons are descriptive observations, not causal explanations.
- The evidence sample sizes for both compared cohorts are retained in the result.

## API

`GET /api/analytics/perceptions/{perception_id}` now includes `cross_lens_analysis` alongside `perspectives`.

The structure is:

```text
cross_lens_analysis
├── status
├── sample_minimum
├── convergence[]
│   ├── dimension
│   ├── cohort_a / cohort_b
│   ├── sample_size_a / sample_size_b
│   ├── leading_stance_a / leading_stance_b
│   ├── shared_themes
│   ├── type
│   └── description
├── divergence[]
└── note
```

## Product meaning

This is the first layer that treats the **difference between legitimate lenses as data**. It should be used to identify where further investigation may be warranted, not to explain why a cohort thinks differently.
