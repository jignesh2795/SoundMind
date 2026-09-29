# SoundMind

Local-first personal music intelligence system.

SoundMind organizes a personal music library using deterministic audio analysis, learned audio embeddings, retrieval fusion, contextual taste modeling, and playlist sequencing.

## Current milestone

M9 — Contextual Taste and Personalization.

The current pipeline now supports:

- evidence: metadata and measured audio features
- Music DNA: structured acoustic evidence derived from stored analysis
- learned representation: optional Discogs-EffNet embeddings
- retrieval: intent matching and learned audio similarity
- ranking: fusion, novelty, diversity, and global/contextual preference
- preference: decayed listening history with context isolation
- sequencing: Smooth, Contrast, Journey, and Discovery playlist modes
- explanations: per-signal ranking contributions

The M9 contextual ranking slice keeps the existing M1 fusion weights and event decay model unchanged. A supplied context selects matching contextual listening evidence; omitting context preserves global preference behavior.

## Architecture

```text
Music source
    ↓
Ingestion / catalog
    ↓
Audio evidence / Music DNA
    ↓
Retrieval
  ├─ metadata + intent
  └─ learned audio similarity
    ↓
Personal ranking
  ├─ global preference
  └─ contextual preference
    ↓
Playlist sequencing
    ↓
Music experience
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
- later: richer contextual personalization, semantic text retrieval, source adapters, editing, stems and advanced creation

See [docs/milestone-status.md](docs/milestone-status.md) for implementation status and the current validation baseline.

This project is local-first and designed to remain usable on modest hardware.
