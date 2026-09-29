# SoundMind

Local-first personal music intelligence system.

SoundMind organizes a personal music library using deterministic audio analysis, learned audio embeddings, retrieval fusion, contextual taste modeling, and playlist sequencing.

## Current milestone

M11.1 — Catalog-Backed Contextual Recommendation.

The current pipeline now supports:

- evidence: metadata and measured audio features
- Music DNA: structured acoustic evidence derived from stored analysis
- learned representation: optional Discogs-EffNet embeddings
- retrieval: intent matching and learned audio similarity
- preference: decayed global and contextual listening history
- personalization: contextual novelty/familiarity from listening exposure
- ranking: existing M1 fusion with contextual preference and novelty signals
- end-to-end context-aware composition across M3, M4, M8, M9, M10, M1, and M2
- catalog-backed recommendation from persisted SQLite tracks and listening events
- sequencing: Smooth, Contrast, Journey, and Discovery playlist modes
- explanations: per-signal ranking contributions

M11.1 adds an application boundary around the existing context-aware flow. It reads active catalog tracks and recent listening events from SQLite, then delegates recommendation logic to the established M10.3 composition.

## Architecture

```text
SQLite catalog + listening history
            ↓
M11 catalog-backed application boundary
            ↓
M10.3 context-aware flow
            ↓
M3 → M4 → M8(optional) → M9 → M10 → M1 → M2
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
- later: CLI/UI recommendation surface, contextual explanations, semantic text retrieval, source adapters, editing, stems and advanced creation

See [docs/milestone-status.md](docs/milestone-status.md) for implementation status and the current validation baseline.

This project is local-first and designed to remain usable on modest hardware.