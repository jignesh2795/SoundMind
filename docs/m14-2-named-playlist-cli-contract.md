# M14.2 — Named Playlist CLI

## Purpose

M14.2 exposes the M14.1 named playlist storage boundary through the CLI.

## Commands

`recommend --save-playlist NAME` saves the final playlist produced by the recommendation workflow.

When `--edit` commands are present, the saved snapshot is the playlist after those edits have been applied.

`--save-playlist` cannot be combined with `--preview-edits`, because M13.7/M13.8 preview mode is explicitly non-mutating.

`playlist list` prints all saved playlist names with item counts in deterministic name order.

`playlist show NAME` loads one saved playlist and prints its ordered track IDs. Name lookup is case-insensitive and uses the M14.1 normalization rules.

Missing named playlists raise an explicit `ValueError`.

## Persistence boundary

The CLI delegates all persistence to `PlaylistRepository`. It does not implement direct SQL operations or introduce a second playlist storage model.

`recommend` continues to use M1 ranking and M2 sequencing before any optional save operation. Playlist editing continues to use the M13 deterministic editing workflow.

## Output

Example:

```text
soundmind recommend "cinematic BGM" --context coding --edit "remove Hero Theme" --save-playlist "Focus Music"

Saved playlist: Focus Music
```

List:

```text
soundmind playlist list

1. Focus Music	8 tracks
```

Show:

```text
soundmind playlist show "Focus Music"

Playlist: Focus Music
1. track-a
2. track-b
```

## Boundaries

M14.2:

- uses the M14.1 repository;
- does not change playlist editing semantics;
- does not re-rank after editing;
- does not re-sequence a saved playlist;
- does not add external synchronization or playback;
- does not introduce an LLM or network dependency.

## Validation

M14.2 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.