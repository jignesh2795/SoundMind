# M12.8 — Configurable Hybrid Retrieval Weights

## Purpose

M12.8 exposes the existing deterministic hybrid lexical/semantic fusion weights through the catalog-backed recommendation boundary.

The hybrid retrieval engine already accepts explicit lexical and semantic weights. M12.8 makes those controls available to `soundmind recommend` so a user can tune the candidate-generation blend before the unchanged M1 ranking stage.

## Scope

M12.8 covers:

- explicit lexical and semantic fusion weights on catalog recommendation;
- CLI flags for `recommend`;
- live hybrid retrieval;
- persisted hybrid retrieval;
- validation through the existing `HybridWeights` contract;
- focused CLI and integration coverage.

M12.8 does not change:

- lexical scoring;
- semantic embedding or cosine scoring;
- query expansion;
- persisted-index freshness or manifest behavior;
- M1 ranking weights or signals;
- contextual preference or novelty;
- M2 sequencing;
- SQLite schema;
- model/provider selection.

## Weight contract

Both weights are numeric, finite, and non-negative.

At least one weight must be positive. The existing `HybridWeights` value normalizes the pair so the effective weights sum to `1.0`.

Defaults remain:

- lexical: `0.5`
- semantic: `0.5`

Examples:

`--lexical-weight 1.0 --semantic-weight 0.0`

uses lexical retrieval as the complete hybrid source weight, while:

`--lexical-weight 0.0 --semantic-weight 1.0`

uses semantic retrieval as the complete hybrid source weight.

Intermediate values provide a deterministic convex blend.

## Recommendation semantics

For `soundmind recommend`, the weights affect only the M12 candidate-generation stage:

```
recommend query
    ↓
lexical retrieval + semantic retrieval
    ↓
per-source normalization
    ↓
configured weighted fusion
    ↓
candidate pool
    ↓
CatalogCandidate adaptation
    ↓
M1 contextual ranking
    ↓
M2 sequencing
```

Therefore the weights can change which tracks enter the candidate pool, but they do not become recommendation-ranking weights.

The default `catalog` recommendation mode is unchanged and does not instantiate text retrieval.

## CLI

Hybrid recommendation examples:

`soundmind recommend "hero BGM" --context coding --retrieval hybrid --lexical-weight 0.7 --semantic-weight 0.3`

`soundmind recommend "hero BGM" --context coding --retrieval hybrid-indexed --lexical-weight 0.3 --semantic-weight 0.7 --text-index data/index/text_vectors`

The same weight flags remain available on `soundmind search --hybrid`.

For non-hybrid retrieval modes, the values are accepted as shared retrieval controls but have no effect on the selected single-source retriever.

## Determinism

Given the same catalog state, query, embedding provider/index state, query expansion setting, weights, retrieval limit, and existing ranking/sequencing inputs, the result remains deterministic.

No LLM, network call, random sampling, or external weighting service is introduced.

## Boundary rationale

M12 remains a candidate-generation layer:

```
M12 retrieval score
    ≠
M1 recommendation score
```

Changing hybrid weights is therefore an explicit retrieval configuration choice rather than a hidden modification to personalization or ranking policy.

## Validation

The implementation branch requires the normal OpenCode Ruff and pytest gate before merge.
