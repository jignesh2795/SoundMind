# SoundMind

Local-first personal music intelligence system.

SoundMind organizes a personal music library using deterministic audio analysis, learned audio embeddings, retrieval fusion, contextual taste modeling, and playlist sequencing.

## Current milestone

M10.2 — Contextual Novelty at the Ranking Boundary.

The current pipeline now supports:

- evidence: metadata and measured audio features
- Music DNA: structured acoustic evidence derived from stored analysis
- learned representation: optional Discogs-EffNet embeddings
- retrieval: intent matching and learned audio similarity
- preference: decayed global and contextual listening history
- personalization: contextual novelty/familiarity evidence from listening exposure
- ranking: existing M1 fusion with preference and contextual novelty signals
- sequencing: Smooth, Contrast, Journey, and Discovery playlist modes
- explanations: per-signal ranking contributions

M10.2 connects contextual novelty to the existing M1 `novelty_score`. It does not modify M1 fusion weights or the `CandidateSignals` schema.

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
Personalization
  ├─ global preference
  ├─ contextual preference
  └─ contextual novelty/familiarity
    ↓
Personal ranking / M1 fusion
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
- M10.1: contextual novelty/familiarity evidence
- M10.2: contextual novelty at the M1 ranking boundary
- later: richer contextual personalization, contextual explanations, semantic text retrieval, source adapters, editing, stems and advanced creation

See [docs/milestone-status.md](docs/milestone-status.md) for implementation status and the current validation baseline.

This project is local-first and designed to remain usable on modest hardware.
