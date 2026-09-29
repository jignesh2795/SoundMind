# M5 — End-to-End Music Flow Contract

## Goal

Prove the existing M3 intent parser, M4 intent retrieval adapter, M1 fusion ranker, and M2 sequence engine can operate as one deterministic local pipeline.

M5 is orchestration only. It does not add filesystem scanning, audio analysis, embeddings, LLM calls, web/YouTube search, persistence, or new candidate metadata extraction.

## Pipeline

```
raw music request
      ↓
M3 parse_intent
      ↓
M4 IntentRetrievalEngine
      ↓
M1 rank_candidates
      ↓
M5 ranked candidates → M2 SequenceCandidate
      ↓
M2 sequence_playlist
      ↓
ordered playlist
```

## Input

An `EndToEndCandidate` contains:

- an M4 `IntentCandidate`
- optional `tempo_bpm`
- optional `brightness`

The optional sequence features are supplied evidence. M5 never derives them.

The wrapped `IntentCandidate` remains the source of intent-retrieval evidence, including energy and novelty.

## Request

An `EndToEndRequest` contains:

- raw natural-language `text`
- candidates
- M2 sequence mode
- optional seed track ID
- result limit
- optional M1 fusion weights

## Output

An immutable `EndToEndResult` contains:

- parsed `MusicIntent`
- ranked M1 candidates
- M2 `SequenceItem` playlist

The ranked candidates remain available for inspection and explanation.

## Behavior

1. Parse the raw request exactly once through M3.
2. Pass the same immutable candidate evidence to M4.
3. Rank through the existing M1 fusion engine.
4. Convert ranked candidates to M2 sequence candidates.
5. Sequence using the requested M2 mode.
6. Return both ranked and sequenced results.

The M5 layer does not duplicate scoring logic from M1, M2, M3, or M4.

## Determinism

For identical request, candidates, weights, and sequence options:

- the parsed intent is identical
- ranking is identical
- playlist ordering is identical
- no randomness or network access occurs
- source candidates are never mutated

## Empty and invalid input

- Empty request text is rejected by M3.
- Duplicate candidate IDs are rejected by M2/M4 boundaries as applicable.
- Invalid candidate ranges are rejected by M4.
- Invalid sequence limits/modes are rejected by M2.
- An empty candidate collection produces an empty ranked result and empty playlist.

## Explicit exclusions

M5 does not:

- scan a music folder
- read audio files
- calculate DSP features
- download or search music
- call an LLM
- persist recommendations
- infer metadata
- modify the M1/M2/M3/M4 contracts
- implement an API or CLI

Those concerns remain separate and can consume this stable orchestration boundary later.
