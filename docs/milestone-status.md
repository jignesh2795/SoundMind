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

## Current M9 state

Branch: `feat/m9-contextual-taste`

Current branch HEAD: `f666767` plus subsequent M9 ranking/test commits.

M9 preserves the existing preference evidence model:

- event types: PLAY, COMPLETE, SKIP, LIKE, DISLIKE, REPLAY
- existing event weights
- 30-day half-life decay
- bounded preference scoring
- caller-supplied timezone-aware reference time

Contextual behavior:

- contexts are normalized strings;
- the initial vocabulary includes coding, work, relax, night, travel, gym, cinematic, and discovery;
- unknown context labels remain supported;
- only events carrying the requested context contribute to contextual preference;
- uncontexted events remain part of global preference;
- omitting context from ranking preserves the existing global preference path;
- supplying context replaces the global preference evidence used for that ranking call with the matching contextual evidence.

M9 does not change the M1 fusion weights, the event model, the decay model, audio analysis, learned embedding model, or database schema.

## Validation baseline

Latest user-reported local gate on the M9 branch:

```text
ruff: All checks passed!
pytest: 101 passed
```

The baseline includes the original 99 M9-first-slice tests plus 2 contextual-ranking tests.

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
M1 Personal Ranking ← M9 Contextual Preference
      ↓
M2 Sequence Engine
      ↓
Ordered playlist
```

M6 provides the catalog adapter that supplies stored SQLite evidence to the pipeline. M8 adds learned track-to-track audio similarity without changing the M1 fusion contract. M9 adds context-specific listening preference at the same ranking boundary.

## Next boundary

The next M9 work should focus on richer contextual personalization without bypassing the established contracts. Potential later layers include contextual novelty/familiarity, context-aware explanations, and stronger integration of context with learned retrieval.

Out of scope for the current M9 slices: LLM inference, automatic context detection, cloud services, CLAP, web/streaming search, schema migration, and generative music.
