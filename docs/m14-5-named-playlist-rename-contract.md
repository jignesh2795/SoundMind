# M14.5 — Named Playlist Rename

## Purpose

M14.5 completes the basic named-playlist identity lifecycle with an explicit rename operation.

## Command

`playlist rename OLD_NAME NEW_NAME` renames one persisted playlist through `PlaylistRepository.rename` and commits the transaction on success.

Both names use the M14.1 display-name normalization and case-insensitive key semantics.

## Persistence semantics

The rename operation changes only:

- `name`;
- `name_key`;
- `updated_at`.

It preserves:

- playlist item membership and order;
- each item's sequence score and base score;
- `created_at`.

A destination name that already exists is rejected with `ValueError`; the existing destination snapshot is never overwritten.

A missing source returns `None` from the repository. The CLI converts that into the existing explicit `ValueError` missing-playlist behavior.

The repository does not commit. The CLI owns the successful transaction commit.

## Boundaries

M14.5 does not:

- re-rank or re-sequence the playlist;
- modify playlist items;
- invoke recommendation generation;
- alter catalog tracks or listening history;
- add playback or external synchronization;
- require an LLM, network service, or cloud model.

## Output

```text
soundmind playlist rename "Focus Music" "Deep Focus"

Renamed playlist: Focus Music -> Deep Focus
```

## Validation

M14.5 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
