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

## Current milestone

### M10.2 — Contextual Novelty at the M1 Ranking Boundary

Branch: `feat/m10-contextual-novelty-ranking`

Base: M10.1 merge `934afde`

M10.2 connects the M10.1 contextual novelty model to the existing M1 ranking boundary.

Ranking behavior:

- a requested context is normalized and matched against event contexts;
- matching contextual exposure is converted to contextual novelty by the M10.1 scorer;
- candidates without matching contextual exposure are treated as unexposed and receive novelty 1.0;
- the resulting value populates the existing `CandidateSignals.novelty_score`;
- existing metadata, DSP, learned, preference, and diversity signals are preserved;
- ranking continues through the existing `rank_candidates()` implementation;
- existing M1 fusion weights remain unchanged;
- input candidates are not mutated.

M9 contextual preference remains a separate signal. The new adapter does not replace or reinterpret preference evidence.

## M10 layering

```text
M10.1
Contextual exposure
      ↓
Contextual novelty/familiarity
      ↓
M10.2
CandidateSignals.novelty_score
      ↓
M1 fusion
      ↓
M2 sequence engine
```

This keeps novelty evidence independent from preference semantics while allowing the established M1 ranker to use it.

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

M6 provides the catalog adapter that supplies stored SQLite evidence to the pipeline. M8 adds learned track-to-track audio similarity without changing the M1 fusion contract. M9 adds context-specific listening preference. M10.1 adds context-specific exposure/novelty evidence, and M10.2 connects that evidence to the existing M1 novelty signal.

## Validation baseline

Latest completed-milestone gate:

```text
M10.2: ruff: All checks passed!
M10.2: pytest: 119 passed
```

M10.2 has been locally validated on branch `feat/m10-contextual-novelty-ranking` at `f283fbf`.

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.