# M10 Contextual Novelty Contract

## Goal

M10 adds contextual novelty and familiarity on top of the existing M9 contextual taste system.

M10.1 derives deterministic contextual exposure and novelty evidence.

M10.2 connects that evidence to the existing M1 ranking boundary by populating the existing `CandidateSignals.novelty_score`.

## Novelty model

Novelty answers:

> How unfamiliar is this track for the requested listening context?

A listening event is treated as exposure to the track for that context.

All existing event types count as exposure:

- PLAY
- COMPLETE
- SKIP
- LIKE
- DISLIKE
- REPLAY

Exposure is recency-decayed with the existing default 30-day half-life.

For a track:

1. Calculate the decayed exposure sum from matching contextual events.
2. Convert the decayed exposure into novelty with:

```text
novelty = 1 / (1 + exposure)
familiarity = 1 - novelty
```

This gives:

- no prior exposure → novelty 1.0
- one fresh exposure → novelty 0.5
- more exposure → lower novelty
- older exposure → lower exposure weight and therefore higher novelty than an equally-sized recent exposure
- repeated exposure → progressively lower novelty

The novelty calculation is independent of the M1 preference event weights. M10 uses event presence as exposure evidence rather than interpreting events as likes or dislikes.

## Context isolation

Only events whose normalized context matches the requested context contribute to contextual novelty.

An event without a context does not contribute to contextual novelty.

A coding exposure therefore does not directly make the same track less novel in the gym context.

## Ranking boundary

M10.2 maps contextual novelty into the existing M1 `CandidateSignals.novelty_score` through a dedicated contextual-novelty ranking adapter.

When a context is supplied:

- contextual novelty replaces the candidate's existing `novelty_score`;
- a candidate with no matching contextual exposure is treated as unexposed and receives novelty 1.0;
- existing `preference_score`, learned similarity, metadata, DSP, and diversity signals are preserved;
- existing M1 fusion weights remain unchanged;
- ranking continues through the existing `rank_candidates()` function.

The adapter does not modify the underlying candidates.

The global ranking path remains unchanged because contextual novelty is opt-in through the new adapter.

## Determinism

Callers supply the reference time.

Given identical events, timestamps, context, candidates, weights, and reference time, the result is deterministic.

Scores are bounded to 0..1.

## Non-goals

M10.2 does not add:

- changes to listening-event schema;
- new event types;
- changes to preference weights;
- changes to preference decay;
- M1 fusion-weight changes;
- changes to `CandidateSignals`;
- LLM inference;
- automatic context detection;
- cloud services;
- web or streaming search;
- audio re-analysis;
- learned embedding model changes.

## Acceptance

M10.2 is complete when:

1. Contextual novelty can populate the existing M1 novelty signal.
2. Unexposed candidates receive novelty 1.0 for the requested context.
3. Context-specific exposure remains isolated.
4. Other M1 signals are preserved.
5. Existing fusion weights and ranking implementation are reused.
6. Inputs are not mutated.
7. Unit tests cover ranking impact, unexposed candidates, context isolation, signal preservation, determinism, and invalid context/time inputs.
