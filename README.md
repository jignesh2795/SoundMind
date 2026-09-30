# SoundMind

Local-first personal music intelligence system.

SoundMind organizes a personal music library using deterministic audio analysis, learned audio embeddings, retrieval fusion, contextual taste modeling, and playlist sequencing.

## Current milestone

M12.3 — Persisted Semantic Retrieval Index.

The current pipeline now supports:

- evidence: metadata and measured audio features
- Music DNA: structured acoustic evidence derived from stored analysis
- learned representation: optional Discogs-EffNet embeddings
- retrieval: intent matching, deterministic catalog text search, optional semantic text retrieval, persisted semantic retrieval, hybrid lexical/semantic fusion, and optional learned audio similarity from a supplied seed
- preference: decayed global and contextual listening history
- personalization: contextual novelty/familiarity from listening exposure
- ranking: existing M1 fusion with contextual preference, novelty, and learned signals
- end-to-end context-aware composition across M3, M4, M8, M9, M10, M1, and M2
- catalog-backed recommendation from persisted SQLite tracks and listening events
- CLI recommendations through the existing soundmind command
- deterministic catalog text search through `soundmind search`
- optional per-signal recommendation explanations
- sequencing: Smooth, Contrast, Journey, and Discovery playlist modes

M11 established the application-facing recommendation and CLI boundaries. M12 adds a separate catalog retrieval layer. M12.1 is the model-free lexical baseline; M12.2 adds explicit local semantic retrieval; M12.3 persists semantic document vectors as derived data with freshness checks. These retrieval paths remain separate from recommendation ranking.

Example:

    soundmind search "hero entry" --limit 10
    soundmind search "calm cinematic background music" --semantic --limit 10
    soundmind search "hero entry" --hybrid --limit 10
    soundmind semantic-index rebuild
    soundmind search "calm cinematic background music" --semantic-indexed --limit 10

Search uses existing title, artist, album, album artist, composer, genre, and file-name metadata. Lexical results are deterministic and stable for the same catalog state and query. Semantic results are stable for the same model, catalog state, and query.

## Architecture

```
CLI search
 ├─ default → M12.1 deterministic text retrieval
 │             ↓
 │          SQLite catalog metadata
 │
 ├─ --semantic → M12.2 local semantic retrieval
 │                 ↓
 │              TextEmbeddingProvider
 │
 └─ --semantic-indexed → M12.3 persisted semantic vectors
                          ↓
                       query embedding + freshness check
```

Recommendation remains separate:

```
CLI recommend
 ↓
M11 application boundary
 ↓
M10.3 context-aware flow
 ↓
M3 → M4 → M8(optional) → M9 → M10 → M1 → M2
 ↓
optional explanation formatting
 ↓
Ordered playlist
```

AI/ML remains an optional enhancement layer around deterministic contracts. The project does not require an LLM or cloud service for the current pipeline.

## Development

Python >= 3.12, uv, SQLite, SQLAlchemy, librosa, soundfile, NumPy.

Optional learned embeddings use ONNX Runtime and a separately cached Discogs-EffNet model.

Validation uses Ruff and pytest.

## Roadmap

- M0: local library ingestion and Music DNA
- M0.6: baseline vector similarity
- M0.7–M0.9: learned audio retrieval
- M1: retrieval fusion
- M1.1: TasteProfile and listening history
- M1.2: preference-aware ranking and recommendation explanations
- M2: playlist sequencing
- M3: natural-language music intent
- M4: intent-aware retrieval
- M5: end-to-end intent-to-playlist flow
- M6: SQLite catalog-to-pipeline integration
- M7: Music DNA enrichment
- M8: learned audio retrieval integration
- M9: contextual taste and contextual ranking
- M10.1: contextual novelty/familiarity evidence
- M10.2: contextual novelty at the M1 ranking boundary
- M10.3: context-aware end-to-end recommendation
- M11.1: catalog-backed contextual recommendation
- M11.2: CLI recommendation surface
- M11.3: seeded learned recommendation
- M11.4: CLI recommendation explanations
- M12.1: deterministic text retrieval foundation
- M12.2: local semantic text retrieval
- M12.3: persisted semantic retrieval index
- M12.4: hybrid lexical/semantic retrieval (in progress)
- later: source adapters, editing, stems and advanced creation

See [docs/milestone-status.md](docs/milestone-status.md) for implementation status and the current validation baseline.

This project is local-first and designed to remain usable on modest hardware.
