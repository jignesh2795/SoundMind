# SoundMind Milestone Status

This document is the project-level implementation ledger. It records completed milestone slices, the current branch state, and the validation baseline.

## Completed milestones

| Milestone | Scope | Status |
|---|---|---|
| M0 | Local ingestion, metadata extraction, bounded DSP analysis, validation, analysis versioning | Complete |
| M0.6 | Baseline DSP vector similarity | Complete |
| M0.7–M0.9 | Discogs-EffNet embeddings, persistent learned index, More Like This | Complete |
| M1 | Retrieval fusion across metadata, DSP, learned, novelty and diversity signals | Complete |
| M1.1 | Persistent listening events and TasteProfile | Complete |
| M1.2 | Preference-aware ranking and recommendation explanations | Complete |
| M2 | Deterministic playlist sequencing: Smooth, Contrast, Journey, Discovery | Complete |
| M3 | Deterministic natural-language MusicIntent parser | Complete |
| M4 | Intent-aware retrieval bridge into M1 CandidateSignals | Complete |
| M5 | End-to-end intent → retrieval → sequencing orchestration | Complete |
| M6 | SQLite catalog → M5 candidate adapter and integration tests | Complete |
| M7 | Deterministic MusicDNA view over stored audio evidence | Complete |
| M8 | Learned audio similarity integrated with M1 ranking and M5 flow | Complete |
| M9.1 | Contextual preference scorer using existing listening events | Complete |
| M9.2 | Contextual preference integrated at the existing M1 ranking boundary | Complete |
| M10.1 | Contextual novelty/familiarity evidence from recency-weighted exposure | Complete |
| M10.2 | Contextual novelty connected to the existing M1 ranking boundary | Complete |
| M10.3 | Context-aware end-to-end recommendation composition | Complete |
| M11.1 | Catalog-backed contextual recommendation from persisted SQLite state | Complete |
| M11.2 | CLI recommendation surface over M11.1 | Complete |
| M11.3 | Seeded learned recommendation through the existing M8 path | Complete |
| M11.4 | CLI recommendation explanations | Complete |
| M12.1 | Deterministic text retrieval foundation over catalog metadata | Complete |
| M12.2 | Local semantic text retrieval with explicit provider boundary | Complete |
| M12.3 | Persisted semantic retrieval index with freshness checks | Complete |
| M12.4 | Hybrid lexical + semantic retrieval fusion | Complete |
| M12.5 | Recommendation retrieval bridge into the existing M1/M2 flow | Complete |
| M12.6 | Configurable text embedding profiles for model-specific query/document prompts | In validation |

## Current milestone

### M12.6 — Configurable Text Embedding Profiles (in validation)

M12.6 makes the text embedding prompt configuration explicit at the provider and persisted-index boundaries. The existing BGE defaults remain unchanged, while models that expect raw text or different prompt conventions can be selected without changing the retrieval engine.

The persisted semantic index records the query/document prefixes alongside the model name. A mismatch is rejected as stale and requires an explicit rebuild.

Local validation is pending; no new test count is recorded here until OpenCode reports the gate.

### M12.5 — Recommendation Retrieval Bridge (completed)

M12.5 was merged into `main` via PR #26, merge commit `9e98846265b1b3d3c6213578f69fc47a0b3dd5f0`.

It connects the M12 catalog retrieval layer to the existing catalog-backed recommendation boundary. The default recommendation path remains the existing full active catalog; explicit retrieval modes can bound the candidate pool before the unchanged contextual ranking and sequencing flow.

Current retrieval modes:

```
catalog          = existing full active-catalog behavior
lexical          = M12.1 deterministic metadata retrieval
semantic         = M12.2 live local semantic retrieval
semantic-indexed = M12.3 persisted semantic retrieval
hybrid           = M12.4 lexical + live semantic retrieval
hybrid-indexed   = M12.4 lexical + persisted semantic retrieval
```

Candidate flow:

```
CLI recommend
    ↓
M12 candidate generation (optional)
    ↓
active TrackRow → CatalogCandidate
    ↓
ContextAwareMusicFlow
    ↓
M1 ranking
    ↓
M2 sequencing
```

M12.5 does not add retrieval scores to M1 ranking. Retrieval supplies the candidate set; M1 remains the ranking authority and M2 remains the sequencing authority.

Default retrieval-pool limit: `max(50, recommendation_limit)`. An explicit retrieval limit may be supplied independently from the final recommendation limit.

Validation:

```
Ruff: All checks passed!
pytest: 201 passed
git diff --check: clean
```

## M12 layering

Lexical path:

```
CLI search / recommend --retrieval lexical
    ↓
CatalogTextSearchService
    ↓
active TrackRow metadata
    ↓
CatalogTextRetrievalEngine
    ↓
track IDs
    ↓
CatalogCandidateRepository.candidates_by_ids
```

Semantic path:

```
CLI search / recommend --retrieval semantic
    ↓
CatalogTextSearchService
    ↓
SemanticTextRetrievalEngine
    ↓
TextEmbeddingProvider
```

Persisted semantic path:

```
semantic-index rebuild
    ↓
active TrackRow metadata
    ↓
TextEmbeddingProvider
    ↓
persisted semantic vectors + manifest

recommend --retrieval semantic-indexed / hybrid-indexed
    ↓
freshness validation
    ↓
query embedding + persisted catalog vectors
```

Hybrid path:

```
CLI search / recommend --retrieval hybrid
    ↓
lexical + semantic retrieval
    ↓
deterministic hybrid union
    ↓
track IDs
    ↓
full CatalogCandidate adaptation
    ↓
existing M1/M2 recommendation flow
```

## Scoring boundaries

Lexical:

```
query tokens
    ↓
metadata token matches
    ↓
fixed field weights
    ↓
coverage-normalized retrieval score
```

Semantic:

```
query vector + catalog vectors
    ↓
cosine similarity
    ↓
semantic retrieval score
```

Hybrid:

```
lexical score + semantic score
    ↓
per-source min-max normalization
    ↓
explicit convex weights
    ↓
hybrid retrieval score
```

Recommendation boundary:

```
M12 retrieval score
    ≠
M1 ranking score
```

M12.5 intentionally does not alter recommendation weights, contextual preference, novelty, learned audio scoring, or sequencing.

## Candidate-pool semantics

M12 retrieval uses a separate candidate-pool limit from the final recommendation limit. For hybrid retrieval, M12.4 applies the candidate limit to each source before fusion. The resulting track IDs are then resolved against active catalog rows so the recommendation flow receives the full structured candidate evidence it already expects.

## Optional AI/ML

Semantic-backed retrieval modes require the optional text-ML provider. The default catalog recommendation path remains model-free. The application does not silently install or download model dependencies.

Text embedding profiles are explicit: model name, query prefix, and document prefix travel together through semantic-index rebuild/search and recommendation candidate generation.

## Future M12 slices

M12.5 completes the retrieval-to-ranking application bridge while retaining a deterministic model-free default. Later slices can add richer retrieval evidence, phrase/synonym expansion, or more advanced recommendation integration without collapsing retrieval and ranking into one boundary.

## Validation baseline

```
M11.4: ruff: All checks passed! / pytest: 136 passed
M12.1: Ruff clean, 147 tests passed
M12.2: Ruff clean, 161 tests passed
M12.3: Ruff clean, 170 tests passed
M12.4: Ruff clean, 194 tests passed
M12.5: Ruff clean, 201 tests passed
```

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.
