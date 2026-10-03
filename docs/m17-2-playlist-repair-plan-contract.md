# M17.2 — Deterministic Playlist Repair Plan

## Purpose

M17.2 adds a read-only repair plan for persisted named playlists with stale catalog references.

## Command

`playlist repair-plan NAME` loads the saved playlist and produces a deterministic action for each persisted track reference.

## Action semantics

Each track is classified using the M17.1 integrity audit:

- `keep` — the catalog contains the track with active status;
- `remove` — the catalog reference is inactive or missing.

The plan preserves the stored playlist order.

## Boundaries

The repair plan:

- does not modify playlist storage;
- does not modify catalog state;
- does not remove any track;
- does not re-rank or re-sequence tracks;
- does not alter scores or timestamps;
- does not require network access, playback, or an LLM.

Actual mutation is intentionally outside M17.2 and must be a separate explicit operation.

## Output

```text
soundmind playlist repair-plan "Focus"

Playlist: Focus
1. track-a	active	keep
2. track-b	inactive	remove
3. track-c	missing	remove
Plan: 1 keep, 2 remove
```

## Validation

M17.2 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
