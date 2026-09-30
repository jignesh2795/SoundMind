# Early Foundation Contracts

This document records the original foundation milestones whose implementation predates the current one-contract-per-slice documentation pattern.

## M0 — Local Library Foundation

Purpose: establish the local-first catalog pipeline.

Core responsibilities:
- scan local music files;
- extract stable metadata and file identity;
- compute bounded deterministic DSP/audio evidence;
- persist catalog evidence in SQLite;
- track analysis version/configuration so cached analysis can be invalidated when its analysis window or offset changes;
- preserve diagnostics for processing failures.

Boundary:

    local files → ingestion → TrackRow → deterministic analysis → stored evidence

Constraints:
- local files are the source input;
- no cloud dependency is required;
- analysis is bounded;
- generated analysis remains reproducible from the same file/configuration.

## M0.6 — Baseline DSP Similarity

Purpose: provide the first vector-similarity retrieval primitive using deterministic audio/DSP evidence.

Boundary:

    stored DSP evidence → vector representation → similarity search

The similarity layer is a retrieval primitive, not a recommendation algorithm. Later ranking layers consume similarity as one signal among several.

## M0.7–M0.9 — Learned Audio Retrieval

Purpose: add learned audio representation on top of the deterministic foundation.

Current representation:

    local track → Discogs-EffNet → 1280-D embedding → persistent NumPy index → cosine similarity

Responsibilities:
- compute learned embeddings from local audio;
- persist vectors as derived/rebuildable artifacts;
- retrieve similar tracks by vector similarity;
- keep SQLite catalog state as the source of truth.

Constraints:
- model-backed retrieval is optional;
- model acquisition is explicit;
- learned indexes are derived data;
- learned retrieval does not imply natural-language text understanding.

## M1 — Retrieval Fusion and Ranking

Purpose: combine retrieval evidence into a deterministic recommendation ranker.

Signal boundary:

    metadata + DSP + learned + preference + novelty + diversity
                         ↓
                    M1 fusion
                         ↓
                    ranked tracks

M1 owns the fusion weights and final candidate ranking. Individual evidence providers should populate their own signal channels without silently changing M1 weights.

The later M3–M12 milestones deliberately preserve this ownership model by adapting new retrieval or personalization evidence into existing ranking boundaries.

## Historical status

These milestones are complete. Their implementation details are retained here as historical foundation context; later milestone-specific contracts contain the more detailed current architecture.