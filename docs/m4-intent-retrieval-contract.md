# M4 Intent-Aware Retrieval Contract

## Goal

Turn a structured M3 `MusicIntent` into deterministic candidate signals that the existing M1 fusion ranker can consume.

M4 is the adapter between intent parsing and retrieval. It does not replace M1 ranking, M2 sequencing, audio analysis, or future semantic/LLM retrieval.

## Boundary

```
MusicIntent
    ↓
IntentCandidate
    ↓
intent match scoring
    ↓
CandidateSignals.metadata_score / dsp_score / novelty_score
    ↓
M1 fusion ranking
    ↓
M2 sequence engine
```

## Candidate model

An `IntentCandidate` represents structured evidence already available for a track:

- track_id
- genres
- moods
- languages
- regions
- energy: normalized 0..1
- instrumentation
- music_types
- scenes
- vocal_preference: any / instrumental / vocal
- novelty_score: normalized 0..1

All collections are expected to be normalized strings.

M4 does not invent missing metadata. Empty candidate fields mean unknown.

## Scoring

Intent matching produces a normalized `intent_score` in 0..1.

Dimension matching is deterministic:

- genres, moods, languages, regions, instrumentation, music_types, scenes: set-overlap when the intent specifies values
- energy: similarity decreases linearly with absolute normalized distance
- vocal preference: exact match scores 1; unknown candidate scores 0.5; conflicting preference scores 0
- negative_terms: a matching excluded characteristic contributes 0 for that dimension
- novelty: use the candidate's supplied novelty score for discovery, and its complement for familiar

Only dimensions explicitly requested by the intent participate in the denominator. This prevents unspecified fields from penalizing a candidate.

A request with no structured constraints returns 0 for intent score rather than treating unknown tracks as matches.

## Mapping into M1

M4 maps the intent score into `metadata_score`.

When an explicit energy target is present, energy similarity is also mapped into `dsp_score`. This is deliberately conservative: M4 does not manufacture BPM, timbre, MFCC, or embedding evidence.

Novelty is mapped to the existing `novelty_score` only when the intent explicitly requests discovery or familiar material.

The returned `CandidateSignals` retain all pre-existing signals and only replace the dimensions M4 is responsible for.

## Determinism

For identical inputs:

- scores are identical
- candidate ordering is stable
- no network calls
- no randomness
- no LLM dependency
- input candidates and intents are never mutated

## Explicit exclusions

Not part of M4:

- database schema expansion for inferred tags
- automatic language detection
- YouTube/web search
- embeddings
- LLM calls
- audio analysis
- playlist sequencing
- recommendation explanations beyond the existing M1 explanation layer

Those can consume this contract later without changing the M3 intent boundary.
