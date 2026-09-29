# M12.1 Deterministic Text Retrieval Contract

## Goal

M12.1 adds a model-free text retrieval foundation over the existing SQLite music catalog.

It is deliberately separate from recommendation ranking. The first slice provides deterministic lexical retrieval that can later be replaced or augmented by semantic embeddings behind the same application boundary.

## Command

    soundmind search "<query>" [--db <path>] [--limit <n>]

The command searches active catalog metadata and prints matches ordered by descending score, then stable track ID.

## Searchable fields

The engine searches existing TrackRow metadata:

- title
- artist
- album
- album artist
- composer
- genre
- file name

Fields have deterministic relevance weights, with title weighted most strongly.

## Scoring

The query is normalized into case-insensitive word tokens.

For each query token, the highest configured weight among fields containing that token contributes to the score.

The final score is:

    sum(best field weight for matched query tokens) / number of query tokens

Therefore:

- exact coverage across high-weight fields scores higher;
- partial query coverage is penalized;
- no matching query tokens produces no result;
- ties are resolved by track ID.

## Flow

    CLI search query
        ↓
    CatalogTextSearchService
        ↓
    active TrackRow records
        ↓
    CatalogTextRetrievalEngine
        ↓
    deterministic TextSearchResult
        ↓
    human-readable CLI output

## Ownership

- `soundmind.cli.main` owns argument parsing and presentation;
- `CatalogTextSearchService` owns SQLite access and active-catalog selection;
- `CatalogTextRetrievalEngine` owns tokenization and lexical scoring;
- recommendation ranking remains owned by the existing M1/M10/M11 stack.

## Mutation and model policy

M12.1 performs no catalog mutations and introduces no database schema.

It does not download models, call cloud services, or invoke an LLM.

## Future semantic layer

M12.1 is intentionally a deterministic lexical baseline.

Future M12 slices may add embedding-based semantic retrieval, synonym/phrase understanding, or hybrid lexical-plus-semantic fusion without making those dependencies mandatory for basic catalog search.

## Acceptance

M12.1 is complete when:

1. active catalog metadata can be searched from the CLI;
2. lexical scoring is deterministic and bounded;
3. multiple metadata fields contribute with fixed weights;
4. partial matches are ranked below full query coverage when otherwise comparable;
5. inactive rows are excluded;
6. tie-breaking is stable;
7. the search path is covered by unit, integration, and CLI tests.
