# M2 Sequence Engine Contract

## Goal

Turn an already-ranked set of music candidates into an ordered playlist using deterministic, explainable rules.

M2 does **not** perform retrieval, natural-language interpretation, LLM reasoning, or audio generation. It consumes candidates and their Music DNA signals and decides sequence order.

## Contract

Input:

- candidate tracks with a stable `track_id`
- normalized `base_score` from M1 retrieval/preference ranking
- optional normalized sequencing features:
  - `energy`: 0..1
  - `tempo_bpm`: positive BPM
  - `brightness`: 0..1
- optional `seed_track_id`
- requested `limit`
- sequence mode

Output:

- ordered immutable `SequenceItem` values
- no duplicate track IDs
- at most `limit` items
- deterministic for identical input/configuration
- never mutates input candidates

## Modes

### Smooth

Prefer continuity between adjacent tracks.

Primary transition costs:

1. energy distance
2. normalized tempo distance
3. brightness distance

M1 base score remains a secondary selection signal.

### Contrast

Prefer deliberate changes between adjacent tracks while retaining reasonable M1 relevance.

The transition objective rewards larger feature distance rather than minimizing it.

### Journey

Create a broad energy arc rather than maximizing local similarity.

The default target curve is:

- start moderate
- build toward higher energy
- finish moderate

The implementation must make the target curve explicit and testable rather than hiding it in heuristic state.

### Discovery

Preserve M1 relevance while increasing novelty/diversity.

Discovery must not invent a novelty signal from unavailable data. The first deterministic implementation may use a supplied `novelty_score`; if absent, novelty contribution is zero.

## Seed behavior

If `seed_track_id` is supplied and present, it is the first item.

If the seed is absent from the candidate set, the engine raises `ValueError` rather than silently substituting another track.

Without a seed, ordering starts from the highest M1 `base_score`, with `track_id` as deterministic tie-breaker.

## Validation

Reject:

- empty track IDs
- duplicate track IDs
- non-finite numeric values
- energy/brightness outside 0..1
- non-positive BPM
- non-positive limits
- unknown sequence modes

A candidate with missing optional sequencing features remains valid. Missing features contribute zero to the corresponding transition objective.

## Selection rule

M2 is a greedy deterministic sequence engine for the initial milestone:

1. establish the first track
2. score every unselected candidate against the current track and sequence mode
3. choose the highest deterministic sequence score
4. repeat until `limit` is reached or candidates are exhausted

Every score must be composed from named, inspectable terms. No randomness.

## Scope exclusions

Not part of M2:

- LLMs
- embeddings generation
- audio decoding
- beat-level transition analysis
- waveform crossfading
- key-aware harmonic mixing
- stem separation
- generative music
- cloud services

Those can be added later as richer transition signals without changing the sequence-engine boundary.
