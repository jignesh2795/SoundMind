# SoundMind Architecture

## System boundary

SoundMind is organized around a stable evidence-to-experience pipeline:

    Music source
        ↓
    ingestion
        ↓
    deterministic analysis / learned representation
        ↓
    retrieval
        ↓
    personal ranking
        ↓
    sequencing
        ↓
    CLI / future user experience

The current implementation keeps these responsibilities explicit rather than building one monolithic recommendation service.

## Source of truth

SQLite stores the catalog and listening history.

    local files
        ↓
    ingestion
        ↓
    SQLite TrackRow / listening events

Derived artifacts are separate:

    audio model → learned vector index
    text model  → semantic text index
    model cache → local runtime cache

A derived artifact must not become the authoritative catalog state.

## Retrieval layers

M3/M4 provide deterministic natural-language intent parsing and intent-aware retrieval.

M8 provides optional track-to-track learned audio similarity.

M12 provides catalog text retrieval:

    query
      ├─ lexical → fixed metadata weights
      ├─ semantic → local text embeddings
      ├─ indexed semantic → persisted document vectors + freshness check
      └─ hybrid → min-max normalized lexical/semantic fusion

These retrieval paths can evolve independently of M1 ranking. Hybrid
retrieval fuses retrieval scores only; it does not change M1 ranking
weights. The pipeline boundary stays:

    retrieval → ranking → sequencing

## Recommendation layers

The current recommendation flow composes:

    M3 → M4 → M8(optional) → M9 → M10 → M1 → M2

Responsibilities remain separated:

- M3: structured MusicIntent
- M4: intent-derived retrieval evidence
- M8: learned audio similarity
- M9: contextual preference
- M10: contextual novelty
- M1: signal fusion and ranking
- M2: playlist sequencing
- M11: SQLite/application and CLI boundaries
- M12: catalog text retrieval

A new retrieval mechanism should normally enrich or feed an existing boundary rather than silently alter ranking weights.

## Determinism

Where reproducibility matters, callers provide:

- reference timestamps;
- explicit query limits;
- explicit model/index paths;
- explicit seed tracks.

Stable tie-breaking and input-order rules are part of the retrieval contracts.

## Optional AI/ML

AI/ML is an enhancement layer, not a prerequisite for the base system.

    deterministic baseline
          ↓
    optional learned representation
          ↓
    optional local semantic model
          ↓
    hybrid lexical/semantic retrieval

Optional dependencies should be loaded at their boundary. Basic catalog search should remain usable without model packages.

## Derived-index lifecycle

Derived indexes follow:

    source-of-truth state
        ↓
    explicit rebuild
        ↓
    persisted derived artifact
        ↓
    freshness validation
        ↓
    query

A stale index should be rejected rather than silently reused.