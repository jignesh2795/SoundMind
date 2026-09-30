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

## Current milestone

### M12.3 — Persisted Semantic Retrieval Index

Branch: `feat/m12-persisted-semantic-index`

Base: M12.2 merge `e3e84a7`

M12.3 persists semantic document vectors as derived data and fingerprints the active catalog plus model so indexed search can reuse vectors safely.

Command:

    soundmind search "<query>" [--db <path>] [--limit <n>]

Behavior:

- searches active SQLite catalog rows only;
- tokenizes query and metadata case-insensitively;
- scores matches using fixed field weights;
- supports title, artist, album, album artist, composer, genre, and file name;
- penalizes partial query coverage;
- resolves ties by stable track ID;
- returns metadata and matched-field evidence;
- does not alter recommendation ranking.

## M12 layering

Lexical path:

```
CLI search
    ↓
CatalogTextSearchService
    ↓
active TrackRow metadata
    ↓
CatalogTextRetrievalEngine
    ↓
TextSearchResult
```

Semantic path:

```
CLI search --semantic
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
NumpyVectorIndex + manifest

CLI search --semantic-indexed
    ↓
active catalog fingerprint check
    ↓
persisted vectors
    ↓
query embedding only
    ↓
SemanticTextSearchResult
```

Both are deliberately separate from:

```
CLI recommend
    ↓
M11 application boundary
    ↓
M10.3 context-aware flow
    ↓
M1 ranking
```

M12 is a retrieval foundation, not a new recommendation algorithm. M12.1 provides the deterministic lexical baseline; M12.2 provides local semantic retrieval; M12.3 persists semantic vectors as derived data.

## Scoring boundaries

Lexical:

```
query tokens
    ↓
metadata token matches
    ↓
fixed field weights
    ↓
coverage-normalized score
    ↓
(-score, track_id)
```

Semantic:

```
query vector + catalog vectors
    ↓
cosine similarity
    ↓
(-score, track_id)
```

M12.3 keeps vectors outside the source-of-truth SQLite catalog. It does not change recommendation weights, invoke an LLM, or require a cloud inference service.

## Future M12 slices

M12.1 lexical retrieval, M12.2 semantic retrieval, and M12.3 persisted semantic retrieval now share the catalog-search boundary. Later slices can add hybrid lexical-plus-semantic fusion, phrase/synonym expansion, or recommendation integration while retaining a model-free fallback.

## Architecture progression

```
CLI
 ↓
M12.1 deterministic text retrieval
 ↓
SQLite catalog metadata
 ↓
future semantic retrieval / hybrid fusion

Recommendation path:
CLI
 ↓
M11 application boundary
 ↓
M10.3 context-aware flow
 ↓
M3 → M4 → M8 → M9 → M10 → M1 → M2
 ↓
optional explanation formatting
 ↓
Ordered playlist
```

## Validation baseline

Latest completed-milestone gate:

```
M11.4: ruff: All checks passed!
M11.4: pytest: 136 passed
```

M12.1 gate: Ruff clean, 147 tests passed.

M12.2 gate: Ruff clean, 161 tests passed.

M12.3 validation is pending the local Ruff and pytest gate on `feat/m12-persisted-semantic-index`.

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.
