# M15.2 — Named Playlist JSON Import

## Purpose

M15.2 provides deterministic local import of the version-1 JSON snapshots produced by M15.1.

## Command

`playlist import INPUT [--name NAME] [--replace-existing]` reads and validates one local JSON snapshot.

When `--name` is omitted, the playlist name embedded in the JSON becomes the saved playlist name.

When `--name` is supplied, it overrides the embedded name for the destination snapshot.

An existing destination is rejected by default. `--replace-existing` must be supplied to replace it.

## Validation

The importer requires:

- JSON object payload;
- `version: 1`;
- non-empty `name`;
- timezone-aware ISO-8601 `created_at`;
- timezone-aware ISO-8601 `updated_at`;
- `items` as an array;
- one-based consecutive item positions;
- non-empty unique `track_id` values;
- finite numeric `sequence_score` and `base_score` values.

The embedded source timestamps are validated as part of the schema but are not written directly into the destination row. New imports use normal repository creation/update timestamps. Replacements use the existing M14.1 save semantics, preserving the destination playlist's original `created_at`.

## Persistence boundary

All persistence remains delegated to `PlaylistRepository.save`.

The repository commits nothing. The CLI commits once after a successful import.

No catalog lookup is required: playlist snapshots intentionally preserve track identifiers even when catalog state changes.

## Boundaries

M15.2 does not:

- re-rank or re-sequence imported tracks;
- regenerate recommendations;
- edit imported playlists;
- change catalog or listening-history state;
- add playback or external synchronization;
- require an LLM, network service, or cloud model.

The JSON document is an interchange representation; SQLite remains the source of truth.

## Output

```text
soundmind playlist import exports/deep-focus.json

Imported playlist: Deep Focus <- exports/deep-focus.json
```

## Validation

M15.2 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

Validated gate at implementation head `52b35636ff1eb0122374b6279bedb745faa5c353`:

```text
Ruff: All checks passed!
pytest: 340 passed, 0 failed
git diff --check: clean
working tree: clean
```

The implementation was merged to `main` as merge commit `daf12922436475339ef9311a36ac55454f78aa42`.
