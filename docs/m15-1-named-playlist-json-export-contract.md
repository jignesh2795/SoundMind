# M15.1 — Named Playlist JSON Export

## Purpose

M15.1 provides a deterministic, local interchange snapshot for persisted named playlists.

## Command

`playlist export NAME OUTPUT` loads an existing named playlist and writes a UTF-8 JSON snapshot to `OUTPUT`.

Name lookup uses the M14.1 whitespace-normalized, case-insensitive name key.

The command does not modify the database and does not commit a transaction.

## JSON schema

The exported object has:

- `version`: integer schema version, currently `1`;
- `name`: persisted display name;
- `created_at`: ISO-8601 playlist creation timestamp;
- `updated_at`: ISO-8601 playlist modification timestamp;
- `items`: ordered snapshot items.

Each item contains:

- `position`: one-based persisted position;
- `track_id`: stable track identifier;
- `sequence_score`: stored M2 sequencing score;
- `base_score`: stored pre-sequencing ranking/base score.

The serializer emits stable indentation, key order, Unicode preservation, and a final newline.

## Boundaries

M15.1 does not:

- update playlist storage;
- re-rank or re-sequence tracks;
- resolve or edit track references;
- alter catalog state or listening history;
- add import semantics;
- add playback or external synchronization;
- require an LLM, network service, or cloud model.

The exported file is a derived interchange representation; the SQLite playlist snapshot remains the source of truth.

## Output

```text
soundmind playlist export "Focus Music" exports/focus.json

Exported playlist: Focus Music -> exports/focus.json
```

Example JSON:

```json
{
  "version": 1,
  "name": "Focus Music",
  "created_at": "2026-10-01T10:00:00+00:00",
  "updated_at": "2026-10-01T11:00:00+00:00",
  "items": [
    {
      "position": 1,
      "track_id": "track-a",
      "sequence_score": 0.9,
      "base_score": 0.8
    }
  ]
}
```

## Validation

M15.1 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

Validated gate at merged implementation head `202316a0579ed87018180c94f5cfba74288cd677`:

```text
Ruff: All checks passed!
pytest: 330 passed, 0 failed
git diff --check: clean
working tree: clean
```

The implementation was merged to `main` as merge commit `9bcecb918a55297a2fac0d5f8eaab9ca5eafeb9a`.
