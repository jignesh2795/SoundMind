# SoundMind Quick Start

## 1. Install

Requirements:
- Python 3.12+
- uv
- a local music directory

From the repository root:

    uv sync --extra dev

## 2. Validate the checkout

Run:

    uv run ruff check .
    uv run pytest

The normal project gate is Ruff plus the full pytest suite.

## 3. Scan a music library

Scan a local music directory into the default SQLite catalog:

    uv run soundmind scan <music-folder>

The default database path is:

    data/database/soundmind.db

Analysis can be disabled for a metadata-only scan:

    uv run soundmind scan <music-folder> --no-analysis

## 4. Search the catalog

Deterministic lexical search:

    uv run soundmind search "hero entry"

Search accepts an explicit database and result limit:

    uv run soundmind search "hero entry" --db <database> --limit 10

## 5. Enable semantic text search

Install the optional text-embedding dependency:

    uv sync --extra text-ml

Then run explicit semantic search:

    uv run soundmind search "calm cinematic background music" --semantic

The model is optional. Ordinary lexical search remains available without it.

## 6. Build a persisted semantic index

Build derived semantic vectors explicitly:

    uv run soundmind semantic-index rebuild

Then query the persisted index:

    uv run soundmind search "calm cinematic background music" --semantic-indexed

The persisted index is derived data. It is fingerprinted against the active catalog and selected model; stale indexes must be rebuilt.

## 7. Hybrid lexical + semantic retrieval

Combine lexical metadata matching with semantic similarity:

    uv run soundmind search "hero entry" --hybrid

Use the persisted index for the semantic side:

    uv run soundmind search "hero entry" \
        --hybrid \
        --semantic-indexed

Tune the convex fusion weights (they must sum positive and are
normalized deterministically):

    uv run soundmind search "hero entry" \
        --hybrid \
        --lexical-weight 0.7 \
        --semantic-weight 0.3

Hybrid retrieval fuses retrieval scores only; it does not change
recommendation ranking. The persisted semantic index must be fresh and
is never rebuilt automatically.

## 8. Learned audio similarity

Learned audio retrieval uses the existing Discogs-EffNet path and is intentionally separate from text search.

Fetch the model explicitly:

    uv run soundmind model fetch-effnet

Rebuild the learned audio index:

    uv run soundmind learned-index rebuild

A seeded recommendation can then use the existing learned path:

    uv run soundmind recommend "<request>" --context <context> --seed-track-id <track-id>

See the M8/M11 contracts for model and index behavior.

## 9. Deterministic recommendation runs

For reproducible recommendation experiments, provide an explicit reference time:

    uv run soundmind recommend "<request>" --context coding --now 2026-09-30T09:00:00+05:30

Use --explain to print the existing ranking contribution details.

## Data directories

Runtime artifacts are intentionally ignored by Git:

    data/database/
    data/index/
    data/models/

Do not commit personal music files, generated databases, model binaries, or derived indexes.