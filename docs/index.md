# SoundMind Documentation

## Project guides

- [Quick Start](quick-start.md) — installation, validation, scanning, search, semantic retrieval, and recommendation.
- [Architecture](architecture.md) — source-of-truth boundaries, retrieval layers, recommendation flow, and derived-index lifecycle.
- [Contributing](../CONTRIBUTING.md) — development workflow, design rules, and pull-request expectations.
- [Milestone Status](milestone-status.md) — current implementation ledger and validation state.

## Milestone contracts

### Foundation

- [Early Foundation Contracts](early-foundation-contracts.md) — M0, M0.6, M0.7–M0.9, and M1.
- [M1.1](m1.1.md)
- [M1.2](m1.2.md)
- [M2](m2-sequence-contract.md)
- [M3](m3-music-intent-contract.md)
- [M4](m4-intent-retrieval-contract.md)
- [M5](m5-end-to-end-contract.md)
- [M6](m6-catalog-pipeline-contract.md)
- [M7](m7-music-dna-contract.md)
- [M8](m8-learned-retrieval-contract.md)

### Personalization and application boundaries

- [M9](m9-contextual-taste-contract.md)
- [M10 contextual novelty](m10-contextual-novelty-contract.md)
- [M10 context-aware recommendation](m10-context-aware-recommendation-contract.md)
- [M11 catalog recommendation](m11-catalog-context-recommendation-contract.md)
- [M11 CLI recommendation](m11-cli-recommendation-contract.md)
- [M11 seeded learned recommendation](m11-seeded-learned-recommendation-contract.md)
- [M11 CLI explanations](m11-cli-explanations-contract.md)

### Retrieval

- [M12.1 deterministic text retrieval](m12-deterministic-text-retrieval-contract.md)
- [M12.2 semantic text retrieval](m12-2-semantic-text-retrieval-contract.md)
- [M12.3 persisted semantic index](m12-3-persisted-semantic-index-contract.md)
- [M12.4 hybrid lexical + semantic retrieval](m12-4-hybrid-retrieval-contract.md)
- [M12.5 recommendation retrieval bridge](m12-5-recommendation-retrieval-contract.md)
- [M12.6 configurable text embedding profiles](m12-6-text-embedding-profiles-contract.md)
- [M12.7 deterministic query expansion](m12-7-query-expansion-contract.md)
- [M12.8 configurable hybrid retrieval weights](m12-8-configurable-hybrid-weights-contract.md)
- [M12.9 deterministic retrieval evidence](m12-9-retrieval-evidence-contract.md)

### Playlist editing

- [M13.1 deterministic playlist editing](m13-1-playlist-editing-contract.md)
- [M13.2 deterministic playlist edit parser](m13-2-playlist-edit-parser-contract.md)
- [M13.3 CLI playlist editing](m13-3-cli-playlist-editing-contract.md)
- [M13.4 relative playlist moves](m13-4-relative-playlist-moves-contract.md)
- [M13.5 catalog track-reference resolution](m13-5-catalog-track-reference-resolution-contract.md)
- [M13.6 deterministic playlist filters](m13-6-deterministic-playlist-filters-contract.md)
- [M13.7 deterministic playlist edit preview](m13-7-playlist-edit-preview-contract.md)
- [M13.8 deterministic playlist edit diff](m13-8-playlist-edit-diff-contract.md)
- [M14.1 named playlist storage](m14-1-named-playlist-storage-contract.md)
- [M14.2 named playlist CLI](m14-2-named-playlist-cli-contract.md)
- [M14.3 persisted playlist editing](m14-3-persisted-playlist-editing-contract.md)
- [M14.4 named playlist deletion](m14-4-named-playlist-deletion-contract.md)
- [M14.5 named playlist rename](m14-5-named-playlist-rename-contract.md)
- [M15.1 named playlist JSON export](m15-1-named-playlist-json-export-contract.md)
- [M15.2 named playlist JSON import](m15-2-named-playlist-json-import-contract.md)
- [M15.3 named playlist JSON import preview](m15-3-named-playlist-json-import-preview-contract.md)
- [M16.1 deterministic M3U8 playlist export](m16-1-m3u8-playlist-export-contract.md)
- [M16.2 deterministic M3U8 playlist import](m16-2-m3u8-playlist-import-contract.md)
- [M16.3 M3U8 playlist import preview](m16-3-m3u8-import-preview-contract.md)

## Documentation rule

Feature work should update the relevant contract, the project-level milestone ledger, and the README when the public project boundary changes. Validation status should only be updated from an actual local gate.

Derived data such as databases, model caches, and vector indexes should be documented separately from source-of-truth application state.
