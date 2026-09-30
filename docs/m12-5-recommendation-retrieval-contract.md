# M12.5 — Recommendation Retrieval Bridge Contract

## Goal

Connect the M12 catalog retrieval layer to the existing catalog-backed recommendation application boundary.

M12.5 is an application-boundary milestone:

```text
M12.5 = retrieval connected to recommendation
M12.5 ≠ new ranking algorithm
M12.5 ≠ AI recommendation
```

The existing M1 ranking and M2 sequencing contracts remain authoritative.

## Current flow

For the default recommendation path, existing behavior remains unchanged:

```text
CLI recommend
    ↓
CatalogContextRecommendationService
    ↓
full active catalog candidates
    ↓
ContextAwareMusicFlow
    ↓
M4 intent retrieval
    ↓
M9/M10 contextual signals
    ↓
M1 ranking
    ↓
M2 sequencing
```

When an explicit M12 retrieval mode is selected:

```text
CLI recommend --retrieval <mode>
    ↓
CatalogContextRecommendationService
    ↓
M12 retrieval candidate generation
    ↓
catalog ID → full CatalogCandidate adaptation
    ↓
existing ContextAwareMusicFlow
    ↓
M1 ranking
    ↓
M2 sequencing
```

## Retrieval modes

The recommendation boundary supports:

```text
catalog
    = existing full active-catalog behavior

lexical
    = M12.1 deterministic metadata retrieval

semantic
    = M12.2 live local semantic retrieval

semantic-indexed
    = M12.3 persisted semantic retrieval

hybrid
    = M12.4 lexical + live semantic retrieval

hybrid-indexed
    = M12.4 lexical + persisted semantic retrieval
```

The default remains `catalog` so existing recommendation behavior does not silently change.

## Candidate pool

M12 retrieval uses a separate candidate-pool limit from the final recommendation limit.

Default:

```text
retrieval_limit = max(50, recommendation_limit)
```

A caller may provide an explicit `--retrieval-limit`.

For hybrid retrieval, the supplied limit is passed to each M12 source before fusion, following the M12.4 fan-in contract.

The final recommendation limit is still applied by the existing M1 ranking boundary.

Therefore:

```text
retrieval_limit
    controls candidate generation

request.limit
    controls final ranked/playlist size
```

## Candidate adaptation

M12 retrieval returns track IDs plus retrieval metadata.

M12.5 does not replace the existing recommendation candidate model with retrieval results.

Instead:

```text
M12 result IDs
    ↓
active TrackRow lookup
    ↓
existing CatalogCandidate
    ↓
EndToEndCandidate
    ↓
existing recommendation flow
```

This preserves stored:

- genre evidence;
- measured energy;
- tempo;
- brightness;
- Music DNA;
- existing CandidateSignals structure.

Inactive or missing catalog rows are not admitted into the recommendation candidate set.

## Ranking boundary

M12 retrieval scores are candidate-generation evidence only.

The M12.4 hybrid score is **not** silently added to M1 scoring:

```text
incorrect:
M1 score + hybrid score

correct:
M12 retrieval → candidate set → existing M1 scoring
```

This keeps retrieval, ranking, and sequencing as separate responsibilities.

## Learned seed behavior

M8/M11 seeded learned retrieval remains inside the existing contextual recommendation flow.

```text
M12 text retrieval
        +
M8 learned seed enrichment
        ↓
existing M1 ranking
```

The two retrieval mechanisms remain separate signals/boundaries.

## Optional semantic dependency

The base recommendation command remains usable with no text-ML dependency because the default retrieval mode is `catalog`.

Semantic, persisted-semantic, hybrid, and hybrid-indexed modes require a text embedding provider.

When those modes are selected without the required provider, the application raises an explicit validation error rather than silently installing, downloading, or changing the fallback mode.

## Persisted semantic behavior

`semantic-indexed` and `hybrid-indexed` reuse the existing M12.3 persisted index lifecycle.

The index:

- remains derived data;
- remains outside SQLite source-of-truth persistence;
- is checked against catalog/model freshness;
- is never automatically rebuilt.

## Determinism

Candidate generation remains deterministic for the same:

- catalog state;
- query;
- retrieval mode;
- retrieval configuration;
- semantic model/index;
- reference recommendation time.

Existing stable track-ID ordering and M1/M2 tie-breaking rules remain unchanged.

## CLI

Recommendation examples:

```bash
soundmind recommend "high energy BGM"     --context coding     --retrieval hybrid
```

With a persisted semantic index:

```bash
soundmind recommend "hero entry"     --context coding     --retrieval hybrid-indexed     --text-model BAAI/bge-small-en-v1.5     --text-index data/index/text_vectors
```

Candidate-pool control:

```bash
soundmind recommend "cinematic BGM"     --context coding     --retrieval hybrid     --retrieval-limit 100     --limit 10
```

## Explicit exclusions

M12.5 does not:

- change M1 fusion weights;
- add hybrid scores to the final ranking score;
- change contextual preference;
- change contextual novelty;
- change learned audio scoring;
- change M2 sequencing;
- add database schema or vector columns;
- change Music DNA;
- add an LLM;
- add cloud inference;
- add synonym or phrase expansion;
- automatically rebuild indexes.

Those remain separate future milestones.
