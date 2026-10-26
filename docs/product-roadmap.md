# SoundMind Product Roadmap

## Product direction

SoundMind is a local-first personal music intelligence system. Its intended user outcome is to turn a person's local music library, music requests, and explicit listening feedback into relevant, explainable recommendations and coherent playlists—without requiring cloud services or paid APIs for the baseline experience.

The architecture already has strong foundations: local catalog ingestion and persisted acoustic evidence; optional learned audio similarity; deterministic and optional semantic text retrieval; intent-aware, contextual, and preference-aware ranking; playlist sequencing and editing; and persisted listening feedback. These capabilities are documented in the [architecture](architecture.md) and completed milestone contracts.

The next phase should measure how well these components serve listeners before adding more independent features.

## Audit findings

### Existing strengths

- The SQLite catalog and listening-event store provide local source-of-truth state.
- Retrieval, ranking, and sequencing have explicit ownership boundaries.
- Model-backed retrieval is optional, and derived indexes are rebuildable artifacts.
- Contextual feedback reaches the existing recommendation path through M18.2.
- The playlist workflow has substantial edit, persistence, import/export, and integrity coverage.

### Gaps that should govern new work

1. **Recommendation evaluation:** the repository has extensive correctness tests, but the current repository tree does not contain a dedicated offline recommendation-quality evaluator, versioned relevance-judgment dataset, or baseline report. Correctness tests do not tell us whether the returned music is relevant.
2. **Intent-to-catalog evidence alignment:** the intent model supports dimensions such as mood, language, scene, genre, instrumentation, and vocal preference, but the active catalog adapter supplies only a subset of corresponding candidate evidence. Unknown evidence must remain distinguishable from a negative match.
3. **Feedback generalization:** existing preference behavior can learn directly from track-level events, but the next step—generalizing a person's feedback to similar, previously unheard tracks—needs a held-out evaluation to show whether it helps.
4. **Music semantics:** the current Music DNA contract is grounded in acoustic measurements. Higher-level properties such as mood, instrumentation, scene, language, and regional context require credible metadata or model-derived evidence; they must not be fabricated from missing fields.
5. **Roadmap balance:** much of M13–M17 expanded playlist operations and hardening. Preserve this functionality, but defer more incremental command variants unless user needs or defects justify them.

These are repository-audit findings, not claims that every current recommendation is poor. They identify what needs to be measured before deciding which algorithm or model is worth changing.

## Planned outcome milestones

### M19 — Recommendation Quality Evaluation Baseline

**Status:** Planned; no evaluator or quality baseline is claimed complete.

Purpose: establish a small, inspectable, repeatable local process for measuring retrieval and recommendation behavior before changing ranking.

Scope:

- Create a curated evaluation set of music requests with track-level relevance judgments and clearly stated coverage limitations. Keep private libraries and private listening histories out of the public repository.
- Build a local evaluator that can compare the existing catalog-backed baseline with lexical retrieval and, when already configured, semantic and hybrid retrieval.
- Calculate ranking metrics such as nDCG@10, Recall@10, and MRR where the evaluation labels support them. Report catalog coverage and missing-evidence rates separately.
- Assess personalization on time-ordered held-out events so future listening does not leak into earlier recommendations. Keep context-specific evaluation isolated.
- Report playlist diagnostics such as repeated-track rate, observed energy trajectory, and transition-feature continuity. Treat these as measurable proxies, not substitutes for listener judgment.
- Record the dataset version, query set, code revision, retrieval mode, candidate limits, weights, optional model/index configuration, metrics, and known limitations alongside each result.
- Use fixtures and temporary databases; remain local-first, deterministic where practical, and independent of cloud APIs or paid services.

Acceptance:

1. A single documented local command reproduces the report for a fixed dataset and configuration.
2. Metric implementations have unit tests and explicit behavior for empty or insufficiently labeled cases.
3. The report includes a baseline for supported modes and clearly identifies unavailable optional modes rather than silently skipping them.
4. The evaluation data and its limitations are versioned and reviewable.
5. No ranking weights are changed merely to make the first benchmark look better; algorithm improvements are separate, measured comparisons against this baseline.

### M20 — Intent-to-Catalog Evidence Alignment

**Status:** Proposed after M19 results identify the most consequential evidence gaps.

Map each supported intent dimension to its actual catalog or derived evidence source, scorer, missing-value policy, and tests. Make supported facets operational end to end; distinguish unknown attributes from known mismatches. Add a dimension only when a credible evidence source exists. Acceptance requires improvement or a justified behavior correction on the M19 evaluation set without regressing existing cases.

### M21 — Feedback-Driven Generalization

**Status:** Proposed after an evaluation baseline exists.

Evaluate whether explicit likes, dislikes, skips, completions, and replays can improve recommendations for similar but previously unheard tracks. Compare against the track-local preference baseline using time-based holdout, context isolation, and appropriate safeguards against leakage. Keep existing behavior as the fallback unless measured evidence justifies a change.

### M22 — Evidence-Guided Music Understanding

**Status:** Long-term direction; scope is intentionally not fixed yet.

Consider richer acoustic representations, optional local models, multilingual catalog evidence, instrumentation and scene descriptors, or advanced creation only when evaluation and observed user needs identify a concrete gap. Model capability alone is not a success criterion. Preserve the deterministic, model-free baseline and explicit derived-index lifecycle.

## Operating rules

- **Measure before tuning.** New weights, retrieval branches, and learned signals should have a reasoned hypothesis and an evaluation comparison.
- **Keep unknown distinct from negative.** Missing genre, language, instrumentation, or semantic annotations are not proof that a candidate is a mismatch.
- **Preserve boundaries.** Retrieval selects candidates, M1 owns ranking, and M2 owns playlist sequencing unless a deliberate contract changes the architecture.
- **Keep ML optional.** Base catalog search and recommendations should continue to work without model downloads, cloud inference, or paid APIs.
- **Prefer outcome slices over tiny milestone churn.** Group implementation tasks under product outcomes; do not add a new milestone just to number the next feature.
- **Pause low-value expansion.** Further playlist command variations, stem separation, and advanced creation remain deferred unless a concrete user workflow or measured gap supports them.
- **Keep regression gates.** Correctness, determinism, data integrity, and exact-SHA local validation remain required, but test count alone is not a measure of product quality.

## Source-of-truth documents

- [Architecture](architecture.md) — existing system boundaries.
- [Milestone Status](milestone-status.md) — completed work, local validation evidence, and the next planned milestone.
- [M18.3 Listening Feedback Summary](m18-3-listening-feedback-summary-contract.md) — read-only inspection of captured feedback.
