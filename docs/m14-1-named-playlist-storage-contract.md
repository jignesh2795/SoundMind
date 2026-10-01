# M14.1 — Named Playlist Storage

## Purpose

M14.1 introduces durable local storage for named playlist snapshots.

The slice creates a persistence boundary for playlists without changing recommendation ranking, sequencing, or the existing deterministic edit engine.

## Storage model

SQLite stores two records:

- `PlaylistRow`: stable numeric identity, normalized display name, case-folded unique name key, creation time, and update time;
- `PlaylistItemRow`: playlist ID, zero-based position, track ID, sequence score, and base score.

Playlist items are stored as an ordered snapshot. The track ID is preserved without requiring a foreign key to the catalog row, so the saved playlist can represent a snapshot even when catalog state later changes.

## Repository contract

`PlaylistRepository` accepts the caller's SQLAlchemy session.

Supported operations:

- `save(name, items, now=...)`: create or replace a named snapshot;
- `get(name)`: load one snapshot or return `None`;
- `list()`: load all snapshots in deterministic case-folded name order.

Names are normalized by collapsing surrounding and repeated whitespace. Name lookup is case-insensitive through a stored `name_key`.

Saving an existing name replaces its item snapshot and updates `updated_at` while preserving `created_at`.

Empty playlists are valid.

Track IDs within one snapshot must be non-empty and unique. Playlist positions are assigned deterministically from item order starting at zero.

`save` does not commit. Transaction ownership remains with the caller.

## Boundaries

M14.1:

- persists only explicit named playlist snapshots;
- preserves sequence/base scores as snapshot metadata;
- uses the existing SQLite/SQLAlchemy storage boundary;
- does not invoke M1 ranking;
- does not invoke M2 sequencing;
- does not alter M13 editing semantics;
- does not add playback, external synchronization, or network dependencies;
- does not add an LLM or semantic playlist generation.

Future slices can add CLI save/load/edit workflows on top of this repository without putting persistence logic into the edit engine.

## Validation

M14.1 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
