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

## Current milestone

### M11.1 — Catalog-Backed Contextual Recommendation

Branch: `feat/m11-catalog-context-recommendation`

Base: M10.3 merge `19cd350`

M11.1 adds an application-facing SQLite boundary around the established M10.3 context-aware recommendation flow.

Persistence path:

```text
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

Behavior:

- active catalog tracks are loaded through the existing catalog repository;
- recent listening events are loaded through the existing event repository;
- event retrieval is bounded by the existing repository limit;
- the caller supplies natural-language text, context, reference time, and recommendation limits through the existing request plus M11 options;
- an optional seed delegates to the existing learned retrieval boundary;
- no new persistence model or schema is introduced;
- recommendation logic remains owned by M10.3 and its existing layers.

## M11 layering

```text
M11.1 persistence boundary
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
```

M11.1 is intentionally an application boundary, not a new recommendation algorithm.

## Architecture progression

```text
SQLite catalog + listening history
              ↓
M11 catalog-backed boundary
              ↓
M10.3 Context-Aware Flow
              ↓
M3 → M4 → M8(optional) → M9 → M10 → M1 → M2
              ↓
        Ordered playlist
```

M6 supplies the catalog adapter. M8 supplies learned track-to-track similarity. M9 supplies contextual preference. M10.1/M10.2 supply and rank contextual novelty. M10.3 composes the signals. M11.1 makes that composition consume persisted SQLite state.

## Validation baseline

Latest completed-milestone gate:

```text
M10.3: ruff: All checks passed!
M10.3: pytest: 127 passed
```

M11.1 has not yet been locally validated in this ledger; its Ruff/pytest result should be recorded after the user runs the gate on the new branch.

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.