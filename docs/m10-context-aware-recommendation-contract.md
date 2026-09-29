# M10 Context-Aware Recommendation Contract

## Goal

M10.3 composes the existing recommendation layers into one context-aware end-to-end path.

The flow combines:

- M3 natural-language MusicIntent;
- M4 intent-aware retrieval;
- M8 learned audio similarity when a seed is supplied;
- M9 contextual preference;
- M10 contextual novelty;
- existing M1 fusion ranking;
- existing M2 playlist sequencing.

## Flow

```text
request text
    ↓
M3 MusicIntent
    ↓
M4 intent retrieval
    ↓
M8 learned audio similarity (optional seed)
    ↓
M9 contextual preference
    ↓
M10 contextual novelty
    ↓
M1 fusion ranking
    ↓
M2 sequencing
```

## Context

The caller supplies a non-empty context and a timezone-aware reference time.

Context matching uses the same normalized string behavior as M9 and M10.

Only events carrying the requested context contribute to contextual preference and contextual novelty.

## Signal ownership

The composed flow preserves signal ownership:

- M4 owns intent-derived metadata, DSP, and intent novelty signals;
- M8 owns learned similarity;
- M9 owns contextual preference;
- M10 owns contextual novelty;
- M1 owns fusion weights and final ranking;
- M2 owns playlist ordering.

When contextual novelty is requested, it replaces the candidate `novelty_score` for that context, following M10.2.

Contextual preference remains the independent `preference_score` signal.

## Learned seed

A seed track is optional.

When supplied, the existing learned retrieval engine is used and the seed is excluded from the recommendation candidates, matching M8 behavior.

When no seed is supplied, existing candidate learned scores are preserved.

If a seed is supplied without a learned retrieval dependency, the flow rejects the request rather than silently skipping the requested learned step.

## Determinism and mutation

Given the same request, events, context, seed, timestamps, reference time, dependencies, and weights, the result is deterministic.

Input candidates and the original request are not mutated.

The flow reuses the existing M1 fusion weights unless the caller supplies explicit weights.

## Non-goals

M10.3 does not add:

- new event types;
- a database schema change;
- changes to M1 fusion weights;
- changes to `CandidateSignals`;
- new audio analysis;
- new embedding models;
- LLM inference;
- automatic context detection;
- cloud services;
- web or streaming search.

## Acceptance

M10.3 is complete when:

1. M3, M4, M8, M9, M10, M1, and M2 can be composed through one flow;
2. contextual preference and contextual novelty reach the existing M1 signals;
3. learned similarity remains optional through the existing seed-based boundary;
4. context-specific evidence remains isolated;
5. existing signal ownership and fusion weights remain unchanged;
6. seed exclusion and request immutability match M8/M5 behavior;
7. unit tests cover combined ranking, context isolation, seed handling, deterministic output, discovery sequencing, and validation.