# M17.3 Active-Catalog Filter Test Hardening

## Purpose

M17.3 hardens regression protection for active-catalog filtering in the three affected playlist paths:

- M13.5 catalog track-reference resolution;
- M13.6 deterministic playlist metadata filters;
- M16.2 deterministic M3U8 playlist import.

The implementation contracts already require inactive catalog tracks to be excluded. M17.3 makes the affected tests exercise that boundary rather than returning pre-filtered fake rows.

## Scope

Only the affected tests are changed.

For M13.5 and M13.6, the test fakes are statement-aware and apply the `TrackRow.status == "active"` predicate from the SQL statement before returning rows.

For M16.2 CLI import, the active-only rule is exercised with both active and inactive catalog rows so removal of the Python-side status filter makes the test fail.

No general test-fixture framework, ORM abstraction, or test infrastructure rewrite is included.

## Regression contract

An inactive catalog track must not participate in:

- title/filename reference resolution for a generated playlist;
- metadata filter matching for a generated playlist;
- M3U8 source-URI import into a named playlist.

Active catalog tracks remain eligible.

## Fail-first validation

The regression tests are considered effective only when the production active-only filters are temporarily removed locally and the affected tests fail, then the filters are restored and the normal gate passes.

Do not commit the temporary production-filter removal.

## Non-goals

M17.3 does not:

- change production filtering logic;
- change playlist semantics;
- add a general statement-aware fake framework;
- add unrelated M15/M16 negative cases;
- change database schema;
- add coverage tooling.

## Validation

The milestone remains in validation until an actual local gate reports:

```text
Ruff: All checks passed!
pytest: <actual count> passed, 0 failed
git diff --check: clean
working tree: clean
```
