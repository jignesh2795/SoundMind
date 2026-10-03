# M17.4 — Playlist Import Negative-Path Hardening

## Purpose

M17.4 closes the identified M15.2 and M16.2 test-validation gaps without changing production behavior.

## M15.2 coverage

Tests cover the contract requirements that were previously under-tested:

- JSON payload must be an object;
- version must be an integer;
- playlist name must be non-empty;
- timestamps must be valid timezone-aware ISO-8601 values;
- `items` must be an array;
- each item must be an object;
- item positions must be integers;
- `track_id` values must be non-empty;
- sequence and base scores must be finite numeric values;
- source timestamps are validated but are not copied into destination playlist timestamps.

The timestamp behavior is verified through a real SQLite-backed CLI import and persisted read-back.

## M16.2 coverage

Tests cover the remaining parser rejection cases:

- consecutive `#EXTINF` entries;
- `#EXTINF` entries without a label;
- duplicate catalog track IDs reached through different source URIs.

The active-catalog source filtering is already protected by M17.3 and is not duplicated here.

## Scope

M17.4 is limited to playlist JSON/M3U8 import tests and the associated milestone documentation.

It does not change production import logic, storage schema, test infrastructure, or unrelated validation debt.

## Validation

The milestone remains in validation until the actual local gate reports:

```text
Ruff: All checks passed!
pytest: <actual count> passed, 0 failed
git diff --check: clean
working tree: clean
```
