# M17.5 — CLI Coverage Hardening

## Purpose

M17.5 closes the identified CLI coverage gap for core local command surfaces without broadening product behavior.

The current target surfaces are:

- `scan`;
- `model fetch-effnet`;
- `learned-index rebuild`;
- `learned-index similar`.

The slice is test-focused. Production changes are allowed only when a test demonstrates an actual contract defect; otherwise the implementation should remain unchanged.

## Scope

### `scan`

Cover:

- required music-folder argument;
- default database path;
- `--no-content-hash`;
- `--no-analysis`;
- analysis duration and offset forwarding;
- scan result/output behavior;
- session/database boundary.

The tests should stub the directory scanner and session factory rather than scanning a real library.

### `model fetch-effnet`

Cover:

- default model destination;
- explicit `--path` forwarding;
- returned model path/output;
- clean handling of the fetch boundary.

Tests must not download a real model or require network access.

### `learned-index rebuild`

Cover:

- database path;
- model path;
- index path;
- optional limit;
- service construction and `rebuild(limit=...)`;
- deterministic output of indexed-count result.

Tests should replace the learned service at the boundary rather than loading ONNX models.

### `learned-index similar`

Cover:

- required track ID;
- database/model/index forwarding;
- limit forwarding;
- deterministic rendering of returned track IDs and scores;
- service boundary without loading the real model/index.

## Contract requirements

The test suite must prove command parsing and wiring rather than merely exercising underlying service methods independently.

At minimum:

1. Each target CLI surface has direct command-level coverage.
2. Defaults are explicit and tested.
3. Explicit path/option overrides are forwarded unchanged.
4. External boundaries are mocked/stubbed and do not require network or heavyweight model assets.
5. CLI output is deterministic for deterministic service results.
6. Existing production services are not duplicated in the test suite.
7. Existing tests remain unchanged in behavior.
8. No unrelated CLI commands are pulled into this milestone unless required to fix a demonstrated contract issue.
9. No persistent state is unintentionally mutated by read-only test paths.
10. Any discovered production defect is covered by a regression test before being fixed.

## Non-goals

M17.5 does not add:

- new CLI commands;
- new ML models;
- automatic model downloads;
- network integration tests;
- real audio-library scans;
- embedding-index rebuilds against large model assets;
- UI/API work;
- recommendation/ranking changes;
- playlist behavior changes;
- database schema changes;
- unrelated coverage cleanup.

## Validation

The milestone remains in validation until the actual local gate reports:

```text
Ruff: All checks passed!
pytest: <actual count> passed, 0 failed
git diff --check: clean
working tree: clean
```

The final report must distinguish new findings from pre-existing repository validation debt.

## Fail-first expectation

Where practical, remove or bypass the specific command-wiring assertion temporarily and verify the targeted test goes RED, then restore the production behavior before the final gate.

The goal is to demonstrate that each test protects a real CLI contract rather than merely increasing line coverage.
