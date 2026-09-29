# M7 Music DNA Contract

## Goal

Expose a typed, deterministic Music DNA representation from the audio evidence
already persisted by the M0 catalog pipeline.

M7 does not change the SQLite schema. The existing catalog remains the source of
truth; `MusicDNA` is a derived read model over stored evidence.

## Pipeline

SQLite TrackRow -> MusicDNA -> EndToEndCandidate.brightness

## Evidence boundary

`MusicDNA` contains measured acoustic evidence only:
- tempo
- RMS-derived energy
- normalized brightness
- spectral bandwidth
- spectral rolloff
- zero-crossing rate
- MFCC vector
- chroma vector

M7 does **not** infer mood, genre, language, region, scene, instrumentation,
vocal type, or music type. Unknown evidence remains `None` or an empty tuple.

## Brightness

Brightness is derived from spectral centroid and sample rate:

`brightness = clamp(spectral_centroid / (sample_rate / 2), 0, 1)`

This uses Nyquist frequency as the normalization boundary. Missing or invalid
sample-rate evidence produces unknown brightness rather than a guess.

## Catalog integration

The catalog adapter creates `MusicDNA` from existing `TrackRow` fields and
carries normalized brightness into M5. No audio is rescanned and no new
analysis is performed during catalog reads.

## Non-goals

- no LLM
- no embedding model
- no cloud service
- no semantic classification
- no schema migration
- no automatic tagging