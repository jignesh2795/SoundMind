# M14.3 — Persisted Playlist Editing CLI

## Purpose

M14.3 extends M14.2 named playlist storage with deterministic editing of an already-saved playlist.

## Command

`playlist edit NAME --edit COMMAND [--edit COMMAND ...]` loads the named snapshot and applies the existing M13 playlist-edit parser and workflow in caller-supplied order.

Name lookup uses the M14.1 normalization rules and is case-insensitive.

`--preview-edits` resolves and applies the same edit plan in memory, prints the command-by-command preview and resulting playlist, and performs no repository save or transaction commit.

Without `--preview-edits`, the final edited snapshot replaces the existing named playlist through `PlaylistRepository.save`, followed by the CLI transaction commit.

At least one `--edit` command is required.

## Semantics

The persisted playlist is the source state. M14.3 does not:

- regenerate recommendations;
- invoke M1 ranking;
- invoke M2 sequencing;
- alter sequence or base scores except by preserving the existing `SequenceItem` values;
- introduce a second edit engine;
- add playback or external playlist synchronization;
- require an LLM, network service, or cloud model.

The existing M13 reference-resolution rules continue to apply, so catalog-aware title/filename references are resolved against the loaded playlist and current catalog state.

## Output

Preview example:

```text
soundmind playlist edit "Focus Music" --edit "remove Hero Theme" --preview-edits

Playlist: Focus Music
Edit preview:
1. command: remove Hero Theme
   → remove hero-theme-id
   changes:
      - remove hero-theme-id from position 2
Playlist preview:
1. track-a
2. track-c
```

Save example:

```text
soundmind playlist edit "Focus Music" --edit "move track-c to 1"

Playlist: Focus Music
1. track-c
2. track-a
Saved playlist: Focus Music
```

## Persistence boundary

All database access remains delegated to `PlaylistRepository`.

A successful non-preview edit replaces only the named playlist snapshot and commits once. A preview never commits.

The playlist's `created_at` remains governed by the M14.1 repository replacement semantics, while `updated_at` changes when a non-preview edit is persisted.

## Validation

M14.3 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
