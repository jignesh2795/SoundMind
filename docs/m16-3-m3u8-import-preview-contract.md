# M16.3 — M3U8 Playlist Import Preview

## Purpose

M16.3 adds a read-only preview mode to the M16.2 local M3U8 import command.

## Command

`playlist m3u8-import INPUT --name NAME [--replace-existing] [--preview]`

With `--preview`, SoundMind parses and resolves the M3U8 input exactly as a real import would, checks destination state, and reports the action without mutating the database.

## Preview semantics

A preview:

- validates the M3U8 header and entry grammar;
- resolves every local source URI against active catalog tracks;
- preserves the same destination naming and replacement rules as a real import;
- reports whether the operation would create, replace, or be blocked.

Preview mode never calls `PlaylistRepository.save` and never commits.

## Boundaries

M16.3 does not:

- change M3U8 parsing or catalog resolution semantics;
- mutate playlist storage;
- change ranking or sequencing;
- regenerate SoundMind scores;
- modify catalog or listening history;
- perform playback or external synchronization;
- require an LLM, cloud model, or network request.

## Output

```text
soundmind playlist m3u8-import exports/focus.m3u8 --name "Focus Music" --preview

M3U8 import preview: exports/focus.m3u8
Playlist: Focus Music
Tracks: 12
Action: create new playlist
```

## Validation

M16.3 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
