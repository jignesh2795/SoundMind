# SoundMind

Local-first personal music intelligence system.

SoundMind organizes a personal music library using deterministic audio analysis, learned audio embeddings, retrieval fusion, contextual taste modeling, and playlist sequencing.

## Current milestone

M15.2 — Named Playlist JSON Import (completed).

The current pipeline now supports:

- evidence: metadata and measured audio features
- Music DNA: structured acoustic evidence derived from stored analysis
- learned representation: optional Discogs-EffNet embeddings
- retrieval: intent matching, deterministic catalog text search, local semantic retrieval, persisted semantic retrieval, hybrid lexical/semantic fusion, and optional learned audio similarity from a supplied seed
- recommendation candidate generation: explicit catalog, lexical, semantic, persisted-semantic, hybrid, and persisted-hybrid retrieval modes
- preference: decayed global and contextual listening history
- personalization: contextual novelty/familiarity from listening exposure
- ranking: existing M1 fusion with contextual preference, novelty, and learned signals
- end-to-end context-aware composition across M3, M4, M8, M9, M10, M1, and M2
- catalog-backed recommendation from persisted SQLite tracks and listening events
- CLI recommendations through the existing soundmind command
- optional per-signal recommendation explanations
- sequencing: Smooth, Contrast, Journey, and Discovery playlist modes
- editing: deterministic post-sequencing playlist edits for removal, absolute/relative movement, swapping, and trimming
- natural-language editing: deterministic parsing of explicit remove, absolute/relative move, swap, and trim commands
- CLI playlist editing: repeatable post-sequencing `--edit` commands on recommendations
- catalog-aware editing: exact title and filename references can resolve to tracks already present in the generated playlist
- playlist filters: deterministic exact artist, album, and genre remove/keep-only commands
- edit preview: deterministic command-by-command playlist edit planning and resulting-playlist preview
- edit diff: deterministic membership and position changes for each previewed edit command
- playlist storage: durable local named playlist snapshots preserving order and sequence/base scores
- playlist CLI: save final recommendation playlists, list/show named snapshots, edit, rename, delete, export, and import saved snapshots deterministically

M11 established the application-facing recommendation and CLI boundaries. M12 adds a separate catalog retrieval layer. M12.1 is the model-free lexical baseline; M12.2 adds explicit local semantic retrieval; M12.3 persists semantic document vectors as derived data with freshness checks; M12.4 fuses lexical and semantic scores into one deterministic union; M12.5 connects those retrieval candidates to the existing recommendation flow; M12.6 makes embedding profiles explicit; M12.7 adds opt-in deterministic music-domain query expansion to lexical retrieval; M12.8 exposes configurable lexical/semantic fusion weights through recommendation candidate generation; M12.9 makes retrieval evidence inspectable without changing ranking. Retrieval remains separate from recommendation ranking: M12 retrieval does not change M1 ranking weights.

## Search examples

    soundmind search "hero entry" --limit 10
    soundmind search "hero bgm" --expand-query --limit 10
    soundmind search "calm cinematic background music" --semantic --limit 10
    soundmind search "hero entry" --hybrid --limit 10
    soundmind search "hero bgm" --hybrid --expand-query --limit 10
    soundmind search "hero bgm" --hybrid --expand-query --explain-retrieval --limit 10
    soundmind search "hero entry" --hybrid --semantic-indexed --limit 10
    soundmind semantic-index rebuild
    soundmind semantic-index rebuild --model <model> --query-prefix "" --document-prefix ""
    soundmind search "calm cinematic background music" --semantic-indexed --limit 10

## Recommendation examples

Existing full-catalog behavior remains the default:

    soundmind recommend "cinematic BGM" --context coding

Use M12 retrieval explicitly for candidate generation:

    soundmind recommend "high energy BGM" \
        --context coding \
        --retrieval hybrid \
        --retrieval-limit 50 \
        --limit 10

Opt into deterministic music-domain query expansion for lexical/hybrid candidate generation:

    soundmind recommend "hero bgm" \
        --context coding \
        --retrieval hybrid \
        --expand-query \
        --lexical-weight 0.7 \
        --semantic-weight 0.3 \
        --limit 10

Edit a generated playlist after sequencing with repeatable commands:

    soundmind recommend "cinematic BGM" \
        --context coding \
        --edit "remove Hero Theme" \
        --edit "move hero-theme.mp3 after Chorus Theme" \
        --edit "remove all tracks by Composer A" \
        --preview-edits

Save a generated or edited playlist by name:

    soundmind recommend "cinematic BGM" \
        --context coding \
        --edit "remove Hero Theme" \
        --save-playlist "Focus Music"

List and inspect saved playlists:

    soundmind playlist list
    soundmind playlist show "Focus Music"

Edit an existing saved playlist without re-ranking or re-sequencing it:

    soundmind playlist edit "Focus Music" \
        --edit "remove Hero Theme" \
        --edit "move night-drive.mp3 to 1"

Preview edits to a saved playlist without persisting changes:

    soundmind playlist edit "Focus Music" \
        --edit "remove Hero Theme" \
        --preview-edits

Delete a saved playlist explicitly:

    soundmind playlist delete "Focus Music"

Rename a saved playlist without changing its tracks or scores:

    soundmind playlist rename "Focus Music" "Deep Focus"

Export a saved playlist as a stable local JSON snapshot:

    soundmind playlist export "Deep Focus" exports/deep-focus.json

Import a JSON playlist snapshot using its embedded name:

    soundmind playlist import exports/deep-focus.json

Import under a different name:

    soundmind playlist import exports/deep-focus.json --name "Coding Focus"

Replace an existing named playlist explicitly:

    soundmind playlist import exports/deep-focus.json --replace-existing

Preview an import without writing the playlist:

    soundmind playlist import exports/deep-focus.json --preview

Export a saved playlist as a player-oriented M3U8 file:

    soundmind playlist m3u8 "Focus Music" exports/focus.m3u8

Import a local M3U8 playlist into a named snapshot:

    soundmind playlist m3u8-import exports/focus.m3u8 --name "Focus Music"

Use the persisted semantic index for the hybrid candidate pool:

    soundmind recommend "hero entry" \
        --context coding \
        --retrieval hybrid-indexed \
        --text-model BAAI/bge-small-en-v1.5 \
        --text-index data/index/text_vectors

M12 retrieval controls the candidate pool; the existing M1 ranking still determines the ranked recommendation and M2 still determines playlist sequencing.

Search uses existing title, artist, album, album artist, composer, genre, and file-name metadata. Lexical results are deterministic and stable for the same catalog state and query. Semantic results are stable for the same model, embedding prompt configuration, catalog state, and query. Query/document prefixes are explicit provider configuration, so models that expect raw text rather than the BGE query/passage convention can be selected without changing the retrieval engine.

## Architecture

```
CLI search
 ├─ default → M12.1 deterministic text retrieval
 │             ↓
 │          SQLite catalog metadata
 │
 ├─ --semantic → M12.2 local semantic retrieval
 │                 ↓
 │              TextEmbeddingProvider
 │
 ├─ --semantic-indexed → M12.3 persisted semantic vectors
 │                           ↓
 │                        query embedding + freshness check
 │
 └─ --hybrid → M12.4 lexical + live semantic
                or lexical + persisted semantic

CLI recommend
 ↓
M12 candidate generation (optional; catalog remains default)
 ↓
CatalogCandidate adapter
 ↓
M11 application boundary
 ↓
M10.3 context-aware flow
 ↓
M1 ranking
 ↓
M2 sequencing
```

Recommendation remains separate from retrieval:

```
M12 retrieval
    ↓
candidate set
    ↓
M1 personal/contextual ranking
    ↓
M2 sequencing
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
- M10.3: context-aware end-to-end recommendation
- M11.1: catalog-backed contextual recommendation
- M11.2: CLI recommendation surface
- M11.3: seeded learned recommendation
- M11.4: CLI recommendation explanations
- M12.1: deterministic text retrieval foundation
- M12.2: local semantic text retrieval
- M12.3: persisted semantic retrieval index
- M12.4: hybrid lexical/semantic retrieval
- M12.5: recommendation retrieval bridge
- M12.6: configurable text embedding profiles
- M12.7: deterministic opt-in music-domain query expansion
- M12.8: configurable hybrid lexical/semantic retrieval weights
- M12.9: deterministic retrieval evidence
- M13.1: deterministic playlist editing primitives
- M13.2: deterministic natural-language playlist edit parser
- M13.3: CLI playlist editing workflow
- M13.4: relative before/after playlist moves
- M13.5: deterministic catalog track-reference resolution
- M13.6: deterministic playlist metadata filters
- M13.7: deterministic playlist edit preview
- M13.8: deterministic playlist edit diff
- M14.1: named playlist storage primitives
- M14.2: named playlist CLI
- M14.3: persisted playlist editing CLI
- M14.4: named playlist deletion
- M14.5: named playlist rename
- M15.1: named playlist JSON export
- M15.2: named playlist JSON import
- M15.3: named playlist JSON import preview
- M16.1: deterministic M3U8 playlist export
- M16.2: deterministic M3U8 playlist import
- later: multilingual catalog evidence, stems and advanced creation

See [docs/milestone-status.md](docs/milestone-status.md) for implementation status and the current validation baseline.

This project is local-first and designed to remain usable on modest hardware.

