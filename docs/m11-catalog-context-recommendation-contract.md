# M11 Catalog-Backed Contextual Recommendation Contract

## Goal

M11 turns the M10.3 context-aware recommendation composition into an application-facing SQLite-backed service.

The first M11 slice reads:

- active tracks from the existing SQLite catalog;
- recent listening events from the existing listening-events table;
- a caller-supplied natural-language request;
- a caller-supplied context and reference time.

It then delegates recommendation behavior to the established M10.3 flow.

## Flow

```text
SQLite tracks
     ↓
CatalogCandidateRepository
     ↓
EndToEndCandidate
     ┐
     ├→ M10.3 ContextAwareMusicFlow
     │
SQLite listening events
     ↓
ListeningEventRepository
     ┘
             ↓
M3 → M4 → M8(optional) → M9 → M10 → M1 → M2
             ↓
      EndToEndResult
```

## Persistence ownership

M11 does not introduce a new persistence model.

- `TrackRow` remains the catalog source of truth;
- `ListeningEventRow` remains the listening-history source of truth;
- `CatalogCandidateRepository` owns catalog-to-candidate adaptation;
- `ListeningEventRepository` owns event retrieval;
- `ContextAwareMusicFlow` owns recommendation composition.

## Retrieval behavior

The service reads only active catalog tracks.

Recent listening events are loaded through the existing repository and bounded by an event limit.

The caller supplies:

- natural-language text;
- normalized or raw context label;
- timezone-aware reference time;
- recommendation limit;
- optional catalog limit;
- optional event limit;
- optional learned-retrieval seed.

When a learned seed is supplied, the caller must inject the existing learned retrieval dependency. M11 does not create or download an embedding model automatically.

## Determinism and mutation

Reference time is supplied by the caller; the service does not use the wall clock for scoring.

Given the same database state, request, context, reference time, limits, dependencies, and weights, the result is deterministic.

The service does not mutate catalog rows or listening events.

## Non-goals

M11.1 does not add:

- new database tables;
- schema migration;
- new listening-event types;
- a new recommendation algorithm;
- a new embedding model;
- automatic model download;
- LLM inference;
- web or streaming search;
- CLI/UI work.

## Acceptance

M11.1 is complete when:

1. active SQLite catalog rows can feed the existing context-aware flow;
2. persisted listening events can contribute contextual preference and novelty;
3. inactive catalog rows are excluded;
4. event retrieval is bounded and delegated to the existing repository;
5. the service reuses M10.3 without changing its ranking contracts;
6. integration tests verify a real SQLite path;
7. caller-supplied reference time keeps the result deterministic.