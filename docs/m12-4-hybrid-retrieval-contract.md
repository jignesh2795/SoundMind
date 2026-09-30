# M12.4 — Hybrid Lexical + Semantic Retrieval Contract

## Goal

Combine the two existing catalog retrieval signals — M12.1 lexical
matching and M12.2/M12.3 semantic similarity — into one deterministic
unified result list.

M12.4 is a retrieval-layer milestone only:

```text
M12.4 = hybrid retrieval
M12.4 ≠ personal ranking
M12.4 ≠ AI recommendation
```

Ranking integration stays explicitly out of scope so a later slice can
consume hybrid results without redesigning this boundary.

## Fusion formula

Each source is first min-max normalized over its own returned
candidates, because raw lexical weights and cosine similarities are not
directly comparable:

```text
normalized = (score - min) / (max - min)
```

- An empty source contributes nothing.
- A source whose scores are all equal maps every candidate to `1.0`.
- A candidate absent from one source scores `0.0` on that source.

The unified score is an explicit convex combination:

```text
hybrid_score =
    lexical_weight * normalized_lexical_score
    +
    semantic_weight * normalized_semantic_score
```

with `lexical_weight + semantic_weight = 1` after normalization.
Non-normalized inputs are accepted and normalized deterministically.
Negative, non-finite, or all-zero weights are rejected with
`ValueError`.

## Candidate handling

The hybrid result is the union of both sources:

```text
union(lexical_candidates, semantic_candidates)
```

A track appearing in only one source remains eligible with `0.0` on
the missing side. Neither source is silently discarded. Duplicate
track IDs within a single source are rejected. Display metadata
(title/artist/album) prefers lexical evidence, then semantic evidence.

## Ordering

Results sort by `(-hybrid_score, track_id)`. At most `limit` items are
returned. Identical inputs always produce identical outputs.

## Persisted semantic path

Hybrid retrieval supports both semantic paths without duplicating
embedding or index logic:

```text
lexical + live semantic → hybrid
lexical + persisted semantic → hybrid
```

The persisted path reuses `PersistentSemanticTextIndex`, including its
model/catalog freshness checks. The index is never rebuilt
automatically. The `provider` remains required on the persisted path
because the query itself is still embedded live; only the catalog
document vectors are reused from storage.

## CLI

```text
soundmind search "<query>" --hybrid [--limit <n>]
soundmind search "<query>" --hybrid --semantic-indexed [--limit <n>]
soundmind search "<query>" --hybrid --lexical-weight 0.7 --semantic-weight 0.3
```

- Default mode remains lexical-only.
- `--semantic` and `--semantic-indexed` remain mutually exclusive.
- `--hybrid` combines lexical results with live semantic results, or
  with persisted-index results when `--semantic-indexed` is also given.
- Weight flags default to `0.5` / `0.5` and are validated by the same
  `HybridWeights` contract.

## Error handling

Explicit `ValueError` for: empty queries, invalid limits, invalid
fusion weights, duplicate candidate IDs, empty catalogs (which yield
an empty result instead), stale persisted indexes (via the existing
`SemanticIndexStaleError`), and unavailable semantic providers (via
the existing optional-dependency error).

## Explicit exclusions

Not part of M12.4:

- personal preference ranking
- contextual/novelty ranking
- sequence engine changes
- recommendation explanations
- database schema changes
- automatic index rebuild
- hybrid ranking fusion
- LLM/cloud behavior
