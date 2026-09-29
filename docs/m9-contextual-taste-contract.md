# M9 Contextual Taste Contract

## Goal

M9 adds context-aware personalization to the existing listening-event preference system.

The existing event evidence remains the source of preference:

- PLAY
- COMPLETE
- SKIP
- LIKE
- DISLIKE
- REPLAY

M9 adds an optional context dimension without replacing the global TasteProfile.

## Context

A context is a stable user-declared or application-supplied label describing the listening situation.

Initial context vocabulary:

- coding
- work
- relax
- night
- travel
- gym
- cinematic
- discovery

Unknown contexts are allowed as normalized strings. M9 does not infer context from audio.

## Evidence

Each listening event may have one optional context.

The existing event weight and 30-day half-life remain unchanged. Contextual evidence is calculated only from events carrying the requested context.

Events without a context contribute to the global preference profile but do not contribute to a context-specific profile.

## Isolation

Contextual preference must not contaminate another context.

For example, a LIKE during coding can strengthen the coding profile but cannot directly strengthen the gym profile.

When no context is requested, the existing global preference behavior remains unchanged.

## Ranking

M9 exposes contextual preference through the existing M1 ranking boundary.

PreferenceAwareRecommender.rank() keeps its current global behavior when context is omitted. When a context is supplied, the recommender uses only contextual preference evidence for the preference_score signal; it does not merge uncontexted global events into that contextual score.

M9 must preserve:

- learned similarity;
- metadata;
- DSP;
- global preference behavior when no context is supplied;
- novelty;
- diversity.

M9 does not change M1 fusion weights.

## Determinism

Given the same events, timestamps, reference time, and requested context, contextual preference must produce the same result.

The implementation must not depend on wall-clock time implicitly; callers supply the reference time.

## Non-goals

M9 does not add:

- LLM inference;
- automatic context detection;
- cloud services;
- a new database schema;
- new event types;
- changes to the existing decay model;
- changes to M1 fusion weights;
- audio re-analysis;
- web or streaming search.

## Acceptance

The M9 contextual ranking slice is complete when:

1. Contextual evidence can be derived from existing listening events.
2. Context-specific events remain isolated.
3. Existing global preference behavior remains intact when no context is supplied.
4. A supplied context reaches the existing M1 preference signal without changing fusion weights.
5. Other candidate signals are preserved.
6. The result is deterministic and bounded.
7. Unit tests cover positive, negative, decay, isolation, empty-context, global-ranking, contextual-ranking, and non-mutation behavior.
