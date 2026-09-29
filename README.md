# SoundMind

Local-first personal music intelligence system.

SoundMind organizes a personal music library using deterministic audio analysis, learned audio embeddings, retrieval fusion, taste modeling, and playlist sequencing.

## Current milestone

M1 — Retrieval Fusion.

The architecture separates:

- evidence: metadata and measured audio features
- learned representation: optional Discogs-EffNet embeddings
- retrieval: similarity and metadata channels
- ranking: fusion, novelty, and diversity
- future preference: TasteProfile and listening history

## Development

Python >= 3.12, uv, SQLite, SQLAlchemy, librosa, soundfile, NumPy.

Optional learned embeddings use ONNX Runtime and a separately cached Discogs-EffNet model.

## Roadmap

- M0: local library ingestion and Music DNA
- M0.6: baseline vector similarity
- M0.7–M0.9: learned audio retrieval
- M1: retrieval fusion
- M1.1: TasteProfile and listening history
- M2: playlist sequencing
- M3: natural-language music intent
- M4: AI DJ and context
- later: source adapters, editing, stems and advanced creation

This project is local-first and designed to remain usable on modest hardware.
