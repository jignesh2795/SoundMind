# M17.1 — Deterministic Playlist Integrity Audit

## Purpose

M17.1 adds a read-only audit for persisted named playlists against the current local catalog.

## Command

`playlist audit NAME` loads the saved playlist and classifies each persisted track reference in playlist order.

## Status semantics

Each track is classified as:

- `active` — the catalog contains the track with active status;
- `inactive` — the catalog contains the track but its status is not active;
- `missing` — the catalog has no row for the persisted track ID.

The report also provides counts for all three states.

## Boundaries

The audit:

- does not modify playlist storage;
- does not modify catalog state;
- does not repair or remove playlist entries;
- does not re-rank or re-sequence tracks;
- does not require network access, playback, or an LLM.

Playlist order is the authoritative order for the diagnostic report.

## Output

```text
soundmind playlist audit "Focus"

Playlist: Focus
1. track-a    active
2. track-b    inactive
3. track-c    missing
Summary: 1 active, 1 inactive, 1 missing
```

## Validation

M17.1 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
