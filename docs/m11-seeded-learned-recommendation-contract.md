# M11.3 Seeded Learned Recommendation Contract

## Goal

M11.3 exposes the existing M8 learned audio retrieval path through the M11 CLI recommendation command.

The slice is optional: normal recommendations remain deterministic and model-free. Learned retrieval activates only when the caller supplies a seed track.

## Command

    soundmind recommend "<request>" --context <context> --seed-track-id <track-id> [options]

Additional options:

- --model: existing Discogs-EffNet ONNX model path;
- --index: existing learned vector index path.

The defaults match the existing learned-index CLI.

## Flow

    CLI
      ↓
    seed_track_id
      ↓
    LearnedEmbeddingService
      ↓
    LearnedRetrievalEngine
      ↓
    ContextAwareMusicFlow
      ↓
    M11.1 catalog + listening history
      ↓
    M3 → M4 → M8 → M9 → M10 → M1 → M2

The seed track is used only to enrich candidates with the existing learned similarity signal. M10.3 continues to exclude the seed itself from the recommendation candidate set.

## Model lifecycle

M11.3 never downloads the model implicitly.

- the model must already exist at --model when learned retrieval is actually executed;
- the explicit `soundmind model fetch-effnet` command remains responsible for model acquisition;
- omitting --seed-track-id does not construct the learned embedding service.

## Ownership

- CLI owns argument parsing and dependency assembly;
- LearnedEmbeddingService owns model/index-backed similarity access;
- LearnedRetrievalEngine maps similarity into the existing M1 learned signal;
- ContextAwareMusicFlow owns composition;
- M11.1 remains the persistence boundary.

## Determinism

Reference time continues to be supplied through --now or the current UTC time.

For the same local files, model, index, database state, request, seed, context, and reference time, the assembled flow preserves the existing deterministic contracts.

## Non-goals

M11.3 does not add:

- a new embedding model;
- automatic model download;
- a new learned-ranking algorithm;
- cloud AI;
- LLM inference;
- new persistence tables;
- GUI work.

## Acceptance

M11.3 is complete when:

1. the CLI accepts an optional learned seed;
2. seed requests construct the existing LearnedEmbeddingService and LearnedRetrievalEngine;
3. non-seeded requests do not construct learned dependencies;
4. model and index paths pass through unchanged;
5. the seed reaches M11.1 and M10.3;
6. unit tests cover both dependency paths;
7. existing M11.2 behavior remains unchanged without a seed.
