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
| M5 | End-to-end intent → retrieval → ranking → sequencing orchestration | Complete |
| M6 | SQLite catalog → M5 candidate adapter and integration tests | Complete |
| M7 | Deterministic MusicDNA view over stored audio evidence | Complete |
| M8 | Learned audio similarity integrated with M1 ranking and M5 flow | Complete |
| M9.1 | Contextual preference scorer using existing listening events | Complete |
| M9.2 | Contextual preference integrated at the existing M1 ranking boundary | Complete |
| M10.1 | Contextual novelty/familiarity evidence from recency-weighted exposure | Complete |
| M10.2 | Contextual novelty connected to the existing M1 ranking boundary | Complete |
| M10.3 | Context-aware end-to-end recommendation composition | Complete |
| M11.1 | Catalog-backed contextual recommendation from persisted SQLite state | Complete |
| M11.2 | CLI recommendation surface over M11.1 | In progress |

## Current milestone

### M11.2 — CLI Recommendation Surface

Branch: `feat/m11-cli-recommendation`

Base: M11.1 merge `66376f7`

M11.2 exposes the existing M11.1 service through the `soundmind recommend` command.

Command:

    soundmind recommend "<natural-language request>" --context <context> [options]

The CLI accepts:

- natural-language request text;
- required context;
- SQLite database path;
- recommendation limit;
- optional catalog limit;
- bounded listening-event limit;
- Smooth, Contrast, Journey, or Discovery sequence mode;
- optional timezone-aware ISO-8601 reference time.

When `--now` is omitted, the CLI supplies the current UTC time. When supplied, `--now` must contain a timezone.

## M11 layering

```
CLI
 ↓
M11.1 catalog-backed application boundary
 ↓
M10.3 context-aware flow
 ├─ M3/M4 intent
 ├─ M8 learned similarity
 ├─ M9 contextual preference
 └─ M10 contextual novelty
 ↓
M1 fusion ranking
 ↓
M2 sequence engine
 ↓
CLI output
```

M11.2 remains a presentation/application boundary. Existing recommendation and persistence contracts remain authoritative.

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
SQLite catalog + listening history
 ↓
M11 application boundary
 ↓
M10.3 Context-Aware Flow
 ↓
M3 → M4 → M8(optional) → M9 → M10 → M1 → M2
 ↓
Ordered playlist
```

## Validation baseline

Latest user-reported M11.1 run:

```
pytest: 130 passed
Ruff: one I001 import-order finding
```

The I001 finding was corrected mechanically in commit `98478bd` before PR #13 was merged. A post-fix local Ruff run has not yet been reported, so M11.1 is not recorded here as fully gate-validated.

M11.2 validation is pending the local Ruff and pytest gate on `feat/m11-cli-recommendation`.

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.
