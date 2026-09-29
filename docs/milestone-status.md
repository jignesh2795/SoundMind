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

## Current milestone

### M10.1 — Contextual Novelty and Familiarity Evidence

Branch: `feat/m10-contextual-novelty`

Base: M9 merge `b8354b2`

M10.1 adds a deterministic, context-specific novelty score derived from existing listening exposure.

Exposure model:

- every existing listening event counts as exposure;
- exposure is filtered by normalized context;
- exposure uses the same 30-day recency half-life concept;
- exposure evidence is separate from the existing preference event weights;
- novelty is `1 / (1 + exposure)`;
- familiarity is the complement, `1 - novelty`.

This makes repeated or recent exposure reduce novelty while older exposure contributes less familiarity.

M10.1 deliberately does not change:

- the listening-event schema;
- event types;
- preference weights;
- preference scoring;
- M1 fusion weights;
- `CandidateSignals`;
- ranking behavior;
- audio analysis;
- learned embedding models;
- database schema.

### M10 next slice

The next M10 slice will connect contextual novelty/familiarity to the existing ranking boundary using the current M1 novelty signal, while preserving the existing global path when no context is requested.

## Architecture progression

```text
M3 MusicIntent
      ↓
M4 Intent Retrieval
      ↓
M7 Music DNA ───────────────┐
      ↓                     │
M8 Learned Audio Retrieval  │
      ↓                     │
Personalization             │
  ├─ global preference      │
  ├─ contextual preference  │
  └─ contextual novelty    │
      ↓                     │
M1 Personal Ranking ←───────┘
      ↓
M2 Sequence Engine
      ↓
Ordered playlist
```

M6 provides the catalog adapter that supplies stored SQLite evidence to the pipeline. M8 adds learned track-to-track audio similarity without changing the M1 fusion contract. M9 adds context-specific listening preference at the same ranking boundary. M10.1 now adds context-specific exposure/novelty evidence without changing that boundary.

## Validation baseline

Latest completed-milestone gate:

```text
M10.1: ruff: All checks passed!
M10.1: pytest: 110 passed
```

M10.1 has been locally validated on branch `feat/m10-contextual-novelty` at `3b1404a`.

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.
