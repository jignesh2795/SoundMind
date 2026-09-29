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

## Current milestone

### M11.4 — CLI Recommendation Explanations

Branch: `feat/m11-cli-explanations` (merged)

Base: M11.3 docs-close merge `6e2a817`

Merge: `63a5a67`

M11.4 exposes the existing `RecommendationExplanation` and `SignalContribution` data through the recommendation CLI.

Command:

    soundmind recommend "<request>" --context <context> --explain [options]

Behavior:

- without `--explain`, the M11.3 output remains unchanged;
- with `--explain`, each ranked candidate prints its strongest signal;
- each existing contribution is printed with raw score, normalized weight, and weighted contribution;
- the CLI only formats fields already produced by the recommendation stack;
- no ranking, fusion, persistence, or model behavior changes.

## M11 layering

```
CLI
 ↓
existing EndToEndResult
 ↓
RecommendationExplanation
 ├─ strongest signal
 └─ per-signal contributions
 ↓
human-readable CLI output
```

M11.4 is intentionally a presentation-only boundary.

## M11.3 seeded learned boundary

```
CLI
 ↓
optional seed
 ↓
M8 LearnedEmbeddingService
 ↓
M8 LearnedRetrievalEngine
 ↓
M11.1 catalog + listening history
 ↓
M10.3 context-aware flow
 ↓
M1 fusion ranking
 ↓
M2 sequence engine
 ↓
CLI output + optional explanation
```

M11.3 activates learned retrieval only for an explicitly supplied seed and never downloads the model implicitly.

## M11.1 persistence boundary

```
SQLite TrackRow records
        ↓
CatalogCandidateRepository
        ↓
EndToEndCandidate

SQLite ListeningEventRow records
        ↓
ListeningEventRepository
        ↓
ListeningEvent

        └──────────────┐
                       ↓
          M10.3 ContextAwareMusicFlow
                       ↓
               EndToEndResult
```

M11.1 uses only active catalog tracks and bounded recent listening history. SQLite timestamps are restored to UTC-aware datetimes at the repository boundary.

## Architecture progression

```
CLI
 ↓
optional seeded M8 learned retrieval
 ↓
SQLite catalog + listening history
 ↓
M11 application boundary
 ↓
M10.3 Context-Aware Flow
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

M11.4 validation is complete: the user-reported local gate on `feat/m11-cli-explanations` passed with Ruff clean and 136 tests.

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.
