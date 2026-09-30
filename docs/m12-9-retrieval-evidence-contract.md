# M12.9 — Deterministic Retrieval Evidence

## Purpose

M12.9 makes retrieval decisions inspectable without changing which retrieval algorithm runs or how recommendation ranking works.

The lexical path reports the winning query variant used for each result. The hybrid path reports normalized source scores and their weighted contributions.

## Scope

M12.9 covers:

- optional lexical evidence identifying the winning query variant;
- optional hybrid evidence exposing normalized lexical/semantic scores;
- weighted lexical/semantic contribution values;
- `soundmind search --explain-retrieval`;
- focused unit coverage.

M12.9 does not change:

- lexical scoring weights or token semantics;
- semantic embeddings or cosine scoring;
- query expansion rules;
- hybrid normalization or weight defaults;
- recommendation candidate limits;
- M1 ranking;
- M2 sequencing;
- SQLite schema;
- persisted-index freshness;
- model/provider behavior.

## Lexical evidence

`TextSearchResult.matched_query` identifies the query variant that produced the selected lexical score for the result.

When expansion is disabled, this is the normalized original query.

When expansion is enabled, it is the deterministic best-scoring variant. Ties are resolved by matched-field ordering and then lexical query-variant ordering.

The evidence is informational; it does not create a second ranking pass.

## Hybrid evidence

`HybridSearchResult` preserves the existing raw source scores and additionally exposes:

- `lexical_normalized_score`;
- `semantic_normalized_score`;
- `lexical_contribution`;
- `semantic_contribution`.

The final hybrid score is the sum of the two contribution values.

Contributions use the same normalized weights already applied by hybrid fusion:

```
lexical contribution
    = normalized lexical score × effective lexical weight

semantic contribution
    = normalized semantic score × effective semantic weight

hybrid score
    = lexical contribution + semantic contribution
```

Missing source scores remain `0.0`, so single-source candidates remain explainable.

## CLI

Default search output is unchanged.

Use:

`soundmind search "hero bgm" --expand-query --explain-retrieval`

to expose the lexical winning query variant.

For hybrid retrieval:

`soundmind search "hero bgm" --hybrid --expand-query --explain-retrieval`

prints normalized source scores and weighted contributions in addition to the existing raw source scores.

## Determinism

For the same catalog state, query, expansion setting, embedding/index state, and hybrid weights, retrieval evidence is deterministic and stable.

No LLM, network service, random sampling, or hidden state is introduced.

## Boundary

Retrieval evidence remains inside M12:

```
retrieval
    ↓
retrieval evidence
    ↓
candidate set

candidate set
    ↓
M1 ranking
    ↓
M2 sequencing
```

Evidence must not be interpreted as an additional M1 ranking signal unless a separate future contract explicitly introduces that behavior.

## Validation

The implementation branch requires the normal OpenCode Ruff and pytest gate before merge.
