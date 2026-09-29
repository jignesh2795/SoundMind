# M10 Contextual Novelty Contract

## Goal

M10 adds contextual novelty and familiarity on top of the existing M9 contextual taste system.

The first M10 slice derives a deterministic novelty score from existing listening events. It does not change ranking yet.

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
2. Convert exposure to novelty with:

```text
novelty = 1 / (1 + exposure)
familiarity = 1 - novelty
```

This gives:

- no prior exposure → novelty 1.0
- more exposure → lower novelty
- older exposure → lower familiarity contribution because of decay
- repeated exposure → progressively lower novelty

The novelty calculation is independent of the M1 preference event weights. M10 uses event presence as exposure evidence rather than interpreting events as likes or dislikes.

## Context isolation

Only events whose normalized context matches the requested context contribute to contextual novelty.

An event without a context does not contribute to contextual novelty.

A coding exposure therefore does not directly make the same track less novel in the gym context.

## Determinism

Callers supply the reference time.

Given identical events, timestamps, context, and reference time, the result is deterministic.

Scores are bounded to 0..1.

## Ranking boundary

The first M10 slice does not change M1 fusion, fusion weights, or `CandidateSignals`.

A later M10 slice may map contextual novelty into the existing M1 `novelty_score` signal.

When no contextual exposure exists for a candidate, the first-slice scorer reports no evidence for that track rather than inventing familiarity.

## Non-goals

M10.1 does not add:

- changes to listening-event schema;
- new event types;
- changes to preference weights;
- changes to preference decay;
- M1 fusion-weight changes;
- LLM inference;
- automatic context detection;
- cloud services;
- web or streaming search;
- audio re-analysis.

## Acceptance

The first M10 slice is complete when:

1. Contextual exposure is derived from existing listening events.
2. Exposure uses the existing 30-day decay concept.
3. Novelty decreases with repeated or recent exposure.
4. Context isolation is preserved.
5. Novelty is bounded and deterministic.
6. No preference semantics or ranking contracts are changed.
7. Unit tests cover no exposure, single exposure, repeated exposure, decay, context isolation, normalization, empty context, and timezone validation.
