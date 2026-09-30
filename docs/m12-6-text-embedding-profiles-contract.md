# M12.6 — Configurable Text Embedding Profiles Contract

## Purpose

M12.6 makes text-embedding prompt configuration an explicit part of SoundMind's semantic retrieval boundary.

The retrieval engine remains provider-agnostic. A text embedding profile binds:

- the embedding model name;
- the query prefix;
- the document prefix.

The existing BGE configuration remains the default:

```
model:          BAAI/bge-small-en-v1.5
query prefix:  query:
document prefix: passage:
```

Empty prefixes are valid for models that expect raw query/document text.

## Scope

M12.6 covers:

1. live semantic retrieval;
2. persisted semantic-index rebuilds;
3. persisted semantic-index freshness validation;
4. hybrid retrieval paths that use semantic retrieval;
5. recommendation candidate retrieval;
6. CLI configuration;
7. compatibility with existing persisted manifests;
8. deterministic configuration propagation.

M12.6 does not change:

- lexical retrieval scoring;
- hybrid fusion mathematics;
- M1 recommendation ranking;
- M2 sequencing;
- SQLite schema;
- vector-index storage format beyond the existing semantic manifest metadata;
- automatic model installation or cloud inference.

## Text embedding profile

The reusable profile is:

```text
TextEmbeddingProfile(
    model_name,
    query_prefix,
    document_prefix,
)
```

The profile is immutable and rejects an empty model name.

The default profile is:

```text
model_name = "BAAI/bge-small-en-v1.5"
query_prefix = "query: "
document_prefix = "passage: "
```

The provider applies the query prefix only to query embedding and the document prefix only to catalog-document embedding.

## Provider boundary

`TextEmbeddingProvider` remains the semantic retrieval abstraction.

The reference FastEmbed adapter accepts the explicit profile configuration and constructs the underlying model from `model_name`.

No retrieval engine logic depends on FastEmbed-specific prompt conventions.

## Persisted semantic indexes

A persisted semantic manifest records:

- index version;
- model name;
- query prefix;
- document prefix;
- embedding dimension;
- catalog fingerprint;
- active track count.

A persisted index is valid only when the requested model and prompt configuration match the manifest.

A mismatch is treated as stale and requires an explicit rebuild.

Existing manifests that predate M12.6 may omit prefix fields. Reads use the historical BGE defaults when those fields are absent, preserving compatibility with indexes created before the profile metadata was introduced.

## CLI contract

Semantic search accepts:

```text
--semantic-model
--semantic-query-prefix
--semantic-document-prefix
```

Semantic-index rebuild accepts:

```text
--model
--query-prefix
--document-prefix
```

Recommendation retrieval accepts:

```text
--text-model
--text-query-prefix
--text-document-prefix
```

The defaults preserve the previous BGE behavior.

## Recommendation boundary

When recommendation retrieval uses semantic, persisted-semantic, hybrid, or persisted-hybrid candidate generation, the same text embedding profile is propagated through candidate retrieval.

M12 retrieval still supplies only the candidate pool.

```
M12 retrieval
    ↓
candidate IDs
    ↓
CatalogCandidate adaptation
    ↓
M1 ranking
    ↓
M2 sequencing
```

Embedding profile configuration does not alter M1 ranking weights or M2 sequencing behavior.

## Determinism and freshness

For a fixed:

- catalog state;
- query;
- model;
- query prefix;
- document prefix;
- provider behavior;

semantic retrieval remains deterministic subject to the provider's deterministic embedding behavior.

Changing the embedding model or either prefix changes the semantic representation contract. Persisted indexes therefore require an explicit rebuild when the requested profile differs from the recorded profile.

## Optional AI/ML boundary

The default catalog recommendation path remains model-free.

Semantic retrieval remains an explicitly selected optional capability. SoundMind does not silently download or install model dependencies for ordinary lexical search or default catalog recommendations.

## Validation

M12.6 was validated by the project-local OpenCode gate before merge:

```
Ruff: All checks passed!
pytest: 208 passed, 0 failed
git diff --check: clean
working tree: clean
```

The 208-test baseline includes the five test-double compatibility fixes made after the initial implementation gate.

## Completion criterion

M12.6 is complete when:

- text embedding model/prompt configuration is explicit;
- live and persisted semantic retrieval share the configuration;
- persisted indexes reject profile mismatches;
- recommendation retrieval propagates the configuration;
- defaults preserve existing BGE behavior;
- documentation records the contract and validation baseline.
