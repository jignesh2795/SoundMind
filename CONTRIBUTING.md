# Contributing to SoundMind

SoundMind is a local-first personal music intelligence project. Contributions should preserve deterministic behavior, explicit dependency boundaries, and the existing milestone-driven architecture.

## Development setup

Requirements:
- Python 3.12 or newer
- uv
- Git

Install the development dependencies:

    uv sync --extra dev

Run the validation gate:

    uv run ruff check .
    uv run pytest

Optional model-backed features have separate extras documented in the main README and milestone contracts.

## Repository structure

    src/soundmind/
        analysis/          deterministic audio/DSP analysis
        domain/            core domain types
        embeddings/        learned-audio embedding adapters
        ingestion/         library scanning and metadata
        preferences/       listening history and personalization
        recommendation/    retrieval, ranking, and explanation
        storage/           SQLite persistence models/boundaries
        vector/            derived vector indexes
        cli/               command-line application surface

    tests/
        unit/               focused component contracts
        integration/        SQLite/application boundary tests

    docs/
        milestone contracts and project implementation ledger

Keep new code close to the boundary it owns. Avoid moving unrelated code during a feature slice.

## Milestone workflow

Each milestone slice should have:

1. a focused feature branch from the current main;
2. a small implementation/test change set;
3. a contract document when the behavior introduces a new boundary;
4. corresponding README/ledger updates when the project boundary changes;
5. a local Ruff + pytest gate;
6. a pull request reviewed against its stated scope.

Use normal merge commits. Do not squash or rebase milestone branches after review.

## Design rules

Preserve these project-wide constraints unless a milestone explicitly changes them:

- SQLite is the catalog/listening-history source of truth.
- Derived indexes and model caches remain separate from source-of-truth persistence.
- Deterministic fallbacks should remain available when optional ML dependencies are absent.
- Reference times should be supplied explicitly at scoring boundaries when determinism matters.
- Retrieval, ranking, and sequencing should remain separate responsibilities.
- New model-backed behavior should be behind an explicit provider/adaptor boundary.
- Avoid automatic model downloads in ordinary commands unless acquisition is the explicit operation.
- Do not mutate caller-owned domain objects when enriching recommendation signals.

## Commit conventions

Use concise conventional-style commit subjects:

    feat: add ...
    fix: correct ...
    test: cover ...
    docs: document ...
    build: update ...

Keep unrelated fixes in separate commits where practical.

## Pull requests

A PR description should state:

- what changed;
- what did not change;
- the test/lint gate;
- the base and intended milestone.

Do not mark validation complete until the local gate has actually run.