# M12.3 — Persisted Semantic Retrieval Index Contract

## Purpose

M12.3 turns M12.2 semantic catalog search into a reusable derived-data index. Catalog metadata is embedded during an explicit rebuild and persisted locally. Search then embeds only the query and reuses the stored document vectors.

## Boundary

```
semantic-index rebuild
    ↓
active TrackRow metadata
    ↓
TextEmbeddingProvider
    ↓
NumpyVectorIndex + manifest
```

Query path:

```
search --semantic-indexed
    ↓
active catalog + model fingerprint validation
    ↓
persisted vectors
    ↓
query embedding
    ↓
cosine similarity
```

## Storage

The persisted semantic index is derived data, not catalog source-of-truth data:

- `<index>.vectors.npy` stores float32 document vectors;
- `<index>.ids.npy` stores track IDs in the same row order;
- `<index>.meta.json` stores index version, model name, query/document prefixes, dimension, catalog fingerprint, and track count;
- `<index>.integrity.json` records the publication signatures for the paired NumPy data files.

The existing `NumpyVectorIndex` persistence boundary is reused.

## Catalog fingerprint

The fingerprint is SHA-256 over active rows sorted by track ID. Each row contributes:

```
track_id + NUL + catalog_text(row) + newline
```

Any change to searchable metadata or active-row membership therefore invalidates the persisted semantic index.

## Model binding

The manifest records the semantic model name and query/document prefixes used to build the index. A search using a different model or prompt configuration is rejected as stale and requires a rebuild.

## Determinism

For the same:

- active catalog;
- catalog metadata;
- embedding model;
- embedding provider behavior;
- query;

the indexed result ordering is deterministic.

Result ordering is:

```
(-cosine_similarity, track_id)
```

## CLI

Build the derived index:

    soundmind semantic-index rebuild

Search it:

    soundmind search "calm cinematic background music" --semantic-indexed

Custom model/index paths remain explicit:

    soundmind semantic-index rebuild --model <model> --query-prefix <prefix> --document-prefix <prefix> --index <path>
    soundmind search "<query>" --semantic-indexed --semantic-model <model> --semantic-query-prefix <prefix> --semantic-document-prefix <prefix> --semantic-index <path>

## Publication integrity

The shared `NumpyVectorIndex` writes new vector and ID files to temporary paths, then publishes each file with atomic replacement and publishes the integrity manifest last. Readers validate both data-file signatures before loading vectors. An interrupted publication is therefore rejected and must be rebuilt rather than serving a mismatched ID/vector pair.

## Safety and freshness

Indexed search must reject a stale catalog or model instead of silently returning results from outdated vectors.

The ordinary lexical command remains model-free:

    soundmind search "<query>"

The M12.2 non-persisted semantic command also remains available:

    soundmind search "<query>" --semantic

## Non-goals

M12.3 does not:

- modify the SQLite schema;
- store vectors inside SQLite;
- automatically rebuild indexes during search;
- alter recommendation ranking;
- invoke an LLM;
- require cloud inference;
- remove M12.1 lexical fallback;
- add hybrid lexical/semantic fusion yet.

## Future extension

A later hybrid-retrieval slice can fuse M12.1 lexical and M12.3 semantic scores using explicit, testable normalization without changing either underlying retrieval engine.
