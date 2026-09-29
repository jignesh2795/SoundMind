# M12.2 — Semantic Text Retrieval Contract

## Purpose

M12.2 adds an optional local semantic-text retrieval path for catalog search. It complements M12.1 lexical search; it does not change recommendation ranking or replace the deterministic fallback.

## Boundary

```
CLI search --semantic
        ↓
CatalogTextSearchService
        ↓
SemanticTextRetrievalEngine
        ↓
TextEmbeddingProvider
        ↓
local text embeddings
```

The engine is provider-agnostic. The reference adapter uses FastEmbed with the local CPU-oriented `BAAI/bge-small-en-v1.5` model.

## Catalog representation

Each active `TrackRow` becomes a stable labeled document containing:

- title
- artist
- album
- album artist
- composer
- genre
- file name

The field labels are included in a fixed order so the same catalog row produces the same document text.

## Query/document embedding

For retrieval-oriented embedding providers:

- the query is encoded as `query: <query>`;
- each catalog document is encoded as `passage: <catalog text>`.

The engine does not persist embeddings or create a new database schema in M12.2.

## Scoring

For each active catalog row:

```
cosine(query_vector, document_vector)
```

Scores are sorted deterministically by:

```
(-score, track_id)
```

The engine returns at most `limit` results.

## Validation

The semantic engine rejects:

- empty queries;
- non-positive or boolean limits;
- duplicate active track IDs;
- mismatched embedding dimensions;
- empty embeddings;
- non-finite embedding values;
- provider result counts that do not match the active catalog row count.

Zero-norm document vectors receive score `0.0`.

## Optional dependency

The default project remains usable without semantic-search dependencies.

Install the optional text-ML extra when semantic retrieval is needed:

    uv sync --extra text-ml

The first semantic search may download the selected model into FastEmbed's local cache. After caching, inference is local.

## Compatibility

M12.1 behavior remains unchanged:

    soundmind search "<query>"

Semantic retrieval is explicitly selected:

    soundmind search "<query>" --semantic

No automatic model download is triggered by ordinary lexical search.

## Non-goals

M12.2 does not:

- alter recommendation ranking weights;
- invoke an LLM;
- require a cloud inference API;
- persist a semantic vector index;
- perform automatic semantic search for recommendations;
- remove the deterministic lexical fallback.

Future slices can add persisted semantic indexes and hybrid lexical/semantic fusion without changing the provider boundary.
