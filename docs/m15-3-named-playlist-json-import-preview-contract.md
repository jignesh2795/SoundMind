# M15.3 — Named Playlist JSON Import Preview

## Purpose

M15.3 adds a read-only preview mode to the M15.2 playlist JSON import command.

## Command

`playlist import INPUT [--name NAME] [--replace-existing] [--preview]` reads and validates the local version-1 JSON snapshot.

With `--preview`, the command resolves the destination name and reports the number of imported tracks plus the action that a real import would take.

## Preview semantics

A preview:

- validates the JSON snapshot using the existing M15.2 importer;
- applies the optional `--name` destination override;
- checks whether the destination playlist already exists;
- reports one of:
  - create new playlist;
  - replace existing playlist, when `--replace-existing` is present;
  - blocked because an existing playlist requires explicit `--replace-existing`.

Preview mode never calls `PlaylistRepository.save` and never commits a transaction.

## Boundaries

M15.3 does not:

- mutate playlist storage;
- alter catalog or listening history;
- re-rank or re-sequence tracks;
- edit imported playlists;
- regenerate recommendations;
- play or synchronize music externally;
- require an LLM, network service, or cloud model.

The existing M15.2 JSON schema and source-timestamp validation remain authoritative. SQLite remains the source of truth.

## Output

New destination:

```text
soundmind playlist import exports/deep-focus.json --preview

Import preview: exports/deep-focus.json
Playlist: Deep Focus
Tracks: 12
Action: create new playlist
```

Existing destination without replacement:

```text
Import preview: exports/deep-focus.json
Playlist: Deep Focus
Tracks: 12
Action: blocked; playlist already exists (use --replace-existing)
```

Existing destination with explicit replacement:

```text
soundmind playlist import exports/deep-focus.json --replace-existing --preview

Import preview: exports/deep-focus.json
Playlist: Deep Focus
Tracks: 12
Action: replace existing playlist
```

## Validation

M15.3 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
