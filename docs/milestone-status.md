# SoundMind Milestone Status

This document is the project-level implementation ledger. It records completed milestone slices, the current branch state, and the validation baseline.

## Completed milestones

| Milestone | Scope | Status |
|---|---|---|
| M0 | Local ingestion, metadata extraction, bounded DSP analysis, validation, analysis versioning | Complete |
| M0.6 | Baseline DSP vector similarity | Complete |
| M0.7–M0.9 | Discogs-EffNet embeddings, persistent learned index, More Like This | Complete |
| M1 | Retrieval fusion across metadata, DSP, learned, novelty and diversity signals | Complete |
| M1.1 | Persistent listening events and TasteProfile | Complete |
| M1.2 | Preference-aware ranking and recommendation explanations | Complete |
| M2 | Deterministic playlist sequencing: Smooth, Contrast, Journey, Discovery | Complete |
| M3 | Deterministic natural-language MusicIntent parser | Complete |
| M4 | Intent-aware retrieval bridge into M1 CandidateSignals | Complete |
| M5 | End-to-end intent → retrieval → sequencing orchestration | Complete |
| M6 | SQLite catalog → M5 candidate adapter and integration tests | Complete |
| M7 | Deterministic MusicDNA view over stored audio evidence | Complete |
| M8 | Learned audio similarity integrated with M1 ranking and M5 flow | Complete |
| M9.1 | Contextual preference scorer using existing listening events | Complete |
| M9.2 | Contextual preference integrated at the existing M1 ranking boundary | Complete |
| M10.1 | Contextual novelty/familiarity evidence from recency-weighted exposure | Complete |
| M10.2 | Contextual novelty connected to the existing M1 ranking boundary | Complete |
| M10.3 | Context-aware end-to-end recommendation composition | Complete |
| M11.1 | Catalog-backed contextual recommendation from persisted SQLite state | Complete |
| M11.2 | CLI recommendation surface over M11.1 | Complete |
| M11.3 | Seeded learned recommendation through the existing M8 path | Complete |
| M11.4 | CLI recommendation explanations | Complete |
| M12.1 | Deterministic text retrieval foundation over catalog metadata | Complete |
| M12.2 | Local semantic text retrieval with explicit provider boundary | Complete |
| M12.3 | Persisted semantic retrieval index with freshness checks | Complete |
| M12.4 | Hybrid lexical + semantic retrieval fusion | Complete |
| M12.5 | Recommendation retrieval bridge into the existing M1/M2 flow | Complete |
| M12.6 | Configurable text embedding profiles for model-specific query/document prompts | Complete |
| M12.7 | Deterministic opt-in music-domain query expansion for lexical retrieval | Complete |
| M12.8 | Configurable hybrid lexical/semantic retrieval weights for recommendation candidate generation | Complete |
| M12.9 | Deterministic retrieval evidence for lexical and hybrid search | Complete |
| M13.1 | Deterministic playlist editing primitives | Complete |
| M13.2 | Deterministic natural-language playlist edit parser | Complete |
| M13.3 | CLI playlist editing workflow after recommendation sequencing | Complete |
| M13.4 | Relative before/after playlist moves | Complete |
| M13.5 | Deterministic catalog track-reference resolution | Complete |
| M13.6 | Deterministic playlist metadata filters | Complete |
| M13.7 | Deterministic playlist edit preview | Complete |
| M13.8 | Deterministic playlist edit diff | Complete |
| M14.1 | Named playlist storage primitives | Complete |
| M14.2 | Named playlist CLI | Complete |
| M14.3 | Persisted playlist editing CLI | Complete |
| M14.4 | Named playlist deletion | Complete |
| M14.5 | Named playlist rename | Complete |
| M15.1 | Named playlist JSON export | Complete |

## Current milestone

### M15.1 — Named Playlist JSON Export (completed)

M15.1 adds a deterministic local JSON export for persisted named playlists. The export contains the playlist identity, UTC timestamps, ordered track IDs, and preserved sequence/base scores, without mutating the database.

Contract: [M15.1 named playlist JSON export](m15-1-named-playlist-json-export-contract.md)

Implementation merge: `9bcecb918a55297a2fac0d5f8eaab9ca5eafeb9a`

Validation:

```text
Ruff: All checks passed!
pytest: 330 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M14.5 — Named Playlist Rename (completed)

M14.5 adds explicit renaming of an existing named playlist. The repository updates only the playlist identity and `updated_at`, preserving the stored items, order, sequence scores, base scores, and original `created_at`.

Rename uses the M14.1 whitespace normalization and case-insensitive name key. Existing destination names are rejected rather than overwritten, and a missing source remains an explicit error at the CLI boundary.

Contract: [M14.5 named playlist rename](m14-5-named-playlist-rename-contract.md)

Implementation merge: `78707100e55564c4e3c9594c366837e5641551ef`

Validation:

```text
Ruff: All checks passed!
pytest: 326 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M14.4 — Named Playlist Deletion (completed)

M14.4 adds explicit deletion of an existing named playlist. The repository removes the snapshot rows through the existing persistence boundary, and the CLI commits the successful deletion.

Deletion uses M14.1 name normalization and is case-insensitive. Missing names remain an explicit error. No recommendation, ranking, sequencing, editing, playback, synchronization, LLM, or network behavior is involved.

Contract: [M14.4 named playlist deletion](m14-4-named-playlist-deletion-contract.md)

Implementation merge: `e2e1848d6882b35a5bc4488ec27829b69c1766bf`

Validation:

```text
Ruff: All checks passed!
pytest: 320 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M14.3 — Persisted Playlist Editing CLI (completed)

M14.3 extends the named playlist CLI with deterministic editing of an already-saved playlist. The command loads the persisted snapshot, applies the existing M13 parser/resolution/editing workflow in caller order, and either previews the resulting state or replaces the same named snapshot.

M14.3 does not re-rank or re-sequence saved items, does not regenerate recommendations, and does not add playback, synchronization, LLM, or network dependencies.

Contract: [M14.3 persisted playlist editing](m14-3-persisted-playlist-editing-contract.md)

Implementation merge: `2d8d46a6a2355e0b66a1793360278be95d9aa3c9`

Validation:

```text
Ruff: All checks passed!
pytest: 315 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M14.2 — Named Playlist CLI (completed)

M14.2 exposes durable named playlist storage through the CLI. Recommendations can save the final generated or edited playlist, and saved playlists can be listed or shown deterministically.

Contract: [M14.2 named playlist CLI](m14-2-named-playlist-cli-contract.md)

Implementation merge: `6682c2a8afc054c982dca6ad1cccdc365c56937a`

Validation:

```text
Ruff: All checks passed!
pytest: 311 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M14.1 — Named Playlist Storage Primitives (completed)

M14.1 introduces durable local storage for named playlist snapshots. The persistence boundary preserves playlist order and sequence/base scores without changing M1 ranking, M2 sequencing, or M13 editing semantics.

Contract: [M14.1 named playlist storage](m14-1-named-playlist-storage-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 307 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.8 — Deterministic Playlist Edit Diff (completed)

M13.8 extends the M13.7 deterministic edit preview with a state diff for each command. The preview reports deterministic playlist membership and position changes between each command's input and output state.

Contract: [M13.8 deterministic playlist edit diff](m13-8-playlist-edit-diff-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 301 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.7 — Deterministic Playlist Edit Preview (completed)

M13.7 adds a preview surface for the existing deterministic playlist-edit workflow. The CLI records parsed commands, resolved structural edits, and the resulting playlist without changing normal ranked output.

Contract: [M13.7 deterministic playlist edit preview](m13-7-playlist-edit-preview-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 298 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.6 — Deterministic Playlist Metadata Filters (completed)

M13.6 adds explicit exact artist, album, and genre filters for already generated playlists. Filter commands are resolved against the current playlist and converted into the existing M13.1 structural removal edits.

Contract: [M13.6 deterministic playlist filters](m13-6-deterministic-playlist-filters-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 296 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.5 — Catalog Track Reference Resolution (completed)

M13.5 resolves exact title and filename references used by playlist edits against the current generated playlist. Exact track IDs remain the primary reference form; ambiguous metadata references are rejected.

Contract: [M13.5 catalog track-reference resolution](m13-5-catalog-track-reference-resolution-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 280 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.4 — Relative Playlist Moves (completed)

M13.4 extends the deterministic M13.1 editor and M13.2 parser with relative movement commands. Users can move an existing track immediately before or after another existing track without calculating an absolute position.

Contract: [M13.4 relative playlist moves](m13-4-relative-playlist-moves-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 272 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.3 — CLI Playlist Editing Workflow (completed)

M13.3 connects M13.2 command parsing and M13.1 structural editing to the existing `recommend` CLI. Repeatable `--edit` commands are applied only after M2 sequencing; ranked recommendation output remains unchanged.

Contract: [M13.3 CLI playlist editing](m13-3-cli-playlist-editing-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 261 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.2 — Deterministic Natural-Language Playlist Edit Parser (completed)

M13.2 converts a small explicit set of natural-language playlist edit commands into M13.1 edit objects. It remains deterministic and does not infer tracks semantically or call an LLM.

Contract: [M13.2 playlist edit parser](m13-2-playlist-edit-parser-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 259 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M13.1 — Deterministic Playlist Editing Primitives (completed)

M13.1 introduces a separate structural-editing layer for already-generated playlists. It supports deterministic removal, movement, swapping, and trimming without changing M1 ranking or M2 sequencing.

Contract: [M13.1 playlist editing primitives](m13-1-playlist-editing-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 234 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M12.9 — Deterministic Retrieval Evidence (completed)

M12.9 makes retrieval decisions inspectable without changing retrieval scoring or recommendation ranking. Lexical results can report the winning query variant, while hybrid results expose normalized source scores and weighted source contributions.

The evidence is informational and remains inside M12. It does not become an M1 ranking signal. The default search output remains unchanged; `--explain-retrieval` is opt-in.

Contract: [M12.9 deterministic retrieval evidence](m12-9-retrieval-evidence-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 220 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M12.8 — Configurable Hybrid Retrieval Weights (completed)

M12.8 exposes the existing deterministic hybrid lexical/semantic fusion weights through the catalog-backed recommendation boundary. Defaults remain 0.5 lexical / 0.5 semantic; configured weights are normalized by the existing HybridWeights contract.

The weights affect only M12 candidate generation for live and persisted hybrid retrieval. M1 ranking and M2 sequencing remain unchanged. The default catalog recommendation path remains model-free and unchanged.

Contract: [M12.8 configurable hybrid retrieval weights](m12-8-configurable-hybrid-weights-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 217 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M12.7 — Deterministic Query Expansion (completed)

M12.7 adds a small, explicit, local vocabulary of music-domain phrase and abbreviation aliases to improve lexical retrieval recall. Expansion is opt-in and deterministic; the original query is always retained.

Expansion affects only lexical retrieval and the lexical side of hybrid candidate generation. Semantic retrieval continues to embed the original query, and M1 ranking/M2 sequencing remain unchanged.

Contract: [M12.7 query expansion](m12-7-query-expansion-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 215 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M12.6 — Configurable Text Embedding Profiles (completed)

M12.6 makes text embedding prompt configuration explicit at the provider and persisted-index boundaries. The existing BGE defaults remain unchanged, while models that expect raw text or different prompt conventions can be selected without changing the retrieval engine.

The persisted semantic index records the query/document prefixes alongside the model name. A mismatch is rejected as stale and requires an explicit rebuild.

M12.6 also propagates the same profile through live semantic search, persisted semantic search, hybrid retrieval, and recommendation candidate generation.

Contract: [M12.6 text embedding profiles](m12-6-text-embedding-profiles-contract.md)

Validation:

```
Ruff: All checks passed!
pytest: 208 passed, 0 failed
git diff --check: clean
working tree: clean
```

### M12.5 — Recommendation Retrieval Bridge (completed)

M12.5 was merged into `main` via PR #26, merge commit `9e98846265b1b3d3c6213578f69fc47a0b3dd5f0`.

It connects the M12 catalog retrieval layer to the existing catalog-backed recommendation boundary. The default recommendation path remains the existing full active catalog; explicit retrieval modes can bound the candidate pool before the unchanged contextual ranking and sequencing flow.

Current retrieval modes:

```
catalog          = existing full active-catalog behavior
lexical          = M12.1 deterministic metadata retrieval
semantic         = M12.2 live local semantic retrieval
semantic-indexed = M12.3 persisted semantic retrieval
hybrid           = M12.4 lexical + live semantic retrieval
hybrid-indexed   = M12.4 lexical + persisted semantic retrieval
```

Candidate flow:

```
CLI recommend
    ↓
M12 candidate generation (optional)
    ↓
active TrackRow → CatalogCandidate
    ↓
ContextAwareMusicFlow
    ↓
M1 ranking
    ↓
M2 sequencing
```

M12.5 does not add retrieval scores to M1 ranking. Retrieval supplies the candidate set; M1 remains the ranking authority and M2 remains the sequencing authority.

Default retrieval-pool limit: `max(50, recommendation_limit)`. An explicit retrieval limit may be supplied independently from the final recommendation limit.

Validation:

```
Ruff: All checks passed!
pytest: 201 passed
git diff --check: clean
```

## M12 layering

Lexical path:

```
CLI search / recommend --retrieval lexical
    ↓
CatalogTextSearchService
    ↓
active TrackRow metadata
    ↓
CatalogTextRetrievalEngine
    ↓
track IDs
    ↓
CatalogCandidateRepository.candidates_by_ids
```

Semantic path:

```
CLI search / recommend --retrieval semantic
    ↓
CatalogTextSearchService
    ↓
SemanticTextRetrievalEngine
    ↓
TextEmbeddingProvider
```

Persisted semantic path:

```
semantic-index rebuild
    ↓
active TrackRow metadata
    ↓
TextEmbeddingProvider
    ↓
persisted semantic vectors + manifest

recommend --retrieval semantic-indexed / hybrid-indexed
    ↓
freshness validation
    ↓
query embedding + persisted catalog vectors
```

Hybrid path:

```
CLI search / recommend --retrieval hybrid
    ↓
lexical + semantic retrieval
    ↓
deterministic hybrid union
    ↓
track IDs
    ↓
full CatalogCandidate adaptation
    ↓
existing M1/M2 recommendation flow
```

## Scoring boundaries

Lexical:

```
query tokens
    ↓
metadata token matches
    ↓
fixed field weights
    ↓
coverage-normalized retrieval score
```

Semantic:

```
query vector + catalog vectors
    ↓
cosine similarity
    ↓
semantic retrieval score
```

Hybrid:

```
lexical score + semantic score
    ↓
per-source min-max normalization
    ↓
explicit convex weights
    ↓
hybrid retrieval score
```

Recommendation boundary:

```
M12 retrieval score
    ≠
M1 ranking score
```

M12.5, M12.6, and M12.7 intentionally do not alter recommendation weights, contextual preference, novelty, learned audio scoring, or sequencing.

## Candidate-pool semantics

M12 retrieval uses a separate candidate-pool limit from the final recommendation limit. For hybrid retrieval, M12.4 applies the candidate limit to each source before fusion. The resulting track IDs are then resolved against active catalog rows so the recommendation flow receives the full structured candidate evidence it already expects.

## Optional AI/ML

Semantic-backed retrieval modes require the optional text-ML provider. The default catalog recommendation path remains model-free. The application does not silently install or download model dependencies.

Text embedding profiles are explicit: model name, query prefix, and document prefix travel together through semantic-index rebuild/search and recommendation candidate generation.

## Future M12 slices

M12.8 completes the hybrid-control extension. Hybrid weights are explicit at both search and recommendation surfaces while remaining confined to candidate generation.

M12.9 completed the retrieval evidence/traceability extension. Future M12 work includes multilingual catalog evidence; playlist editing now begins separately at M13.1. Such work should remain behind explicit contracts and should not collapse retrieval and recommendation ranking into one boundary.

## Validation baseline

```
M11.4: ruff: All checks passed! / pytest: 136 passed
M12.1: Ruff clean, 147 tests passed
M12.2: Ruff clean, 161 tests passed
M12.3: Ruff clean, 170 tests passed
M12.4: Ruff clean, 194 tests passed
M12.5: Ruff clean, 201 tests passed
M12.6: Ruff clean, 208 tests passed
M12.7: Ruff clean, 215 tests passed
M12.8: Ruff clean, 217 tests passed
M12.9: Ruff clean, 220 tests passed
M13.1: Ruff clean, 234 tests passed
M13.2: Ruff clean, 259 tests passed
M13.3: Ruff clean, 261 tests passed
M13.4: Ruff clean, 272 tests passed
M13.5: Ruff clean, 280 tests passed
M13.6: Ruff clean, 296 tests passed
M13.7: Ruff clean, 298 tests passed
M13.8: Ruff clean, 301 tests passed
M14.1: Ruff clean, 307 tests passed
M14.2: Ruff clean, 311 tests passed
M14.3: Ruff clean, 315 tests passed
M14.4: Ruff clean, 320 tests passed
M14.5: Ruff clean, 326 tests passed
M15.1: Ruff clean, 330 tests passed
```

## Documentation rule

Every milestone slice should update:

1. its contract document;
2. the project-level milestone ledger;
3. the README current milestone/roadmap when the project boundary changes;
4. validation status only after the local gate is actually run.

This keeps GitHub documentation aligned with the implementation state rather than relying on conversation history.
