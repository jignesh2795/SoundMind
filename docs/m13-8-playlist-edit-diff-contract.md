# M13.8 — Deterministic Playlist Edit Diff

## Purpose

M13.8 extends the M13.7 deterministic edit preview with a state diff for each parsed command.

The diff explains which tracks changed membership or position between the playlist state before a command and the resulting state after that command.

## Contract

For each command in the existing `plan_playlist_edit_commands(...)` workflow:

1. start from the current playlist state;
2. resolve the command using the existing M13.5/M13.6 resolution paths;
3. apply the existing M13.1 structural edits;
4. compare the pre-command and post-command playlist states;
5. record deterministic `PlaylistEditChange` entries alongside the existing plan step.

A change contains:

- `track_id`;
- `from_position`, a zero-based prior position or `None` when the track was not present;
- `to_position`, a zero-based resulting position or `None` when the track was removed.

Human-readable descriptions use one-based display positions.

## Ordering

Changes are deterministic:

- existing tracks are considered in their pre-command playlist order;
- additions, if ever produced by a future edit layer, are considered in resulting playlist order;
- unchanged tracks are omitted.

Current M13.1–M13.7 edit commands only remove or reorder tracks, so normal M13.8 output reports removals and position changes.

## CLI behavior

`recommend --preview-edits` keeps the M13.7 command-by-command preview and adds a `changes:` section for each command.

Example:

```text
Edit preview:
1. command: move c to position 1
   → move c to position 1
   changes:
      - move a from position 1 to position 2
      - move b from position 2 to position 3
      - move c from position 3 to position 1
Playlist preview:
1. c
2. a
3. b
```

The normal ranked recommendation section is unchanged.

## Boundaries

M13.8:

- reuses the existing M13.1 editing engine;
- reuses M13.5 track-reference resolution and M13.6 metadata filters;
- reuses M13.7 command planning;
- does not persist edit history;
- does not mutate external playlist state;
- does not add tracks, replacement discovery, fuzzy matching, semantic matching, playback, or re-ranking;
- does not introduce an LLM or network dependency.

The diff is an informational state comparison over the existing in-memory playlist workflow.

## Validation

M13.8 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The exact test count must be recorded only after the local gate is reported.
