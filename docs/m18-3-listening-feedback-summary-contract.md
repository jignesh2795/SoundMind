# M18.3 — Listening Feedback Summary CLI

## Purpose

Make the persisted listening-feedback data inspectable without opening SQLite or changing how recommendations score events. The new command summarizes the most recent events by event type and normalized context, including the number of distinct tracks represented in each context.

## Baseline

Base: `main` at `cacfce600f1cfe363e12c36ec00d4fe1937e80ad`.

Reuse the M18.1 event capture/listing command and `ListeningEventRepository`. The summary is a read-only view of existing data; it does not add a table, alter event records, or introduce a second persistence path.

## CLI contract

Command:

```text
soundmind event summary [--limit N] [--db PATH]
```

- `--db` defaults to `data/database/soundmind.db`.
- `--limit` defaults to 1000 and must satisfy the existing repository's positive-limit validation.
- The summary covers only the most recent `N` events returned by the existing repository. It must not imply it summarizes older events outside this bounded window.
- Output includes the window limit, total events in the returned window, distinct tracks, counts for every event type, and per-context event/track counts.
- Event types appear in the stable `ListeningEventType` declaration order, including zero counts.
- Context labels are normalized with the same `strip().lower()` semantics used by contextual preference scoring. Blank and absent contexts share the `(none)` bucket. Context buckets are sorted alphabetically, with `(none)` last.
- The command is read-only and never changes event or catalog state.
- Empty history prints zero totals and zero for each event type, with an explicit empty context section.

## Example output

```text
Listening summary (most recent 10 events)
Events: 2
Distinct tracks: 2
By event type:
  play: 0
  complete: 0
  skip: 1
  like: 1
  dislike: 0
  replay: 0
By context:
  coding: 1 event, 1 track
  workout: 1 event, 1 track
```

## Non-goals

- No change to global or contextual preference scoring, novelty, ranking weights, or recommendation results.
- No event deletion, editing, aggregation by time bucket, export format, or database migration.
- No automatic playback observation or external-player integration.
- No new dependencies, network calls, model loading, or cloud service.

## Validation gate

Run on the exact candidate SHA in an isolated worktree:

```bash
uv sync --extra dev
uv run pytest tests/unit/test_listening_summary.py tests/unit/cli/test_listening_cli.py tests/integration/test_listening_summary_integration.py
uv run ruff check .
uv run pytest
git diff --check
git status --short
```

Record exact base/candidate SHAs, focused and full test results, Ruff and diff-check results, changed-file scope, and confirmation that the existing checkout remains unchanged. Do not mark validation complete until the local gate has actually passed.

## Acceptance

M18.3 is complete when:
- the public CLI reports counts from persisted events using the bounded recent-event window;
- context normalization and deterministic ordering are covered by unit tests;
- a real temporary-SQLite test covers both populated and empty history;
- the full local Ruff + pytest gate passes on the exact candidate SHA;
- production scoring and persistence behavior remain unchanged.


## Exact-SHA Validation Record — PASS

- Base SHA: `cacfce600f1cfe363e12c36ec00d4fe1937e80ad`.
- Candidate SHA: `f3d848075fd8aef51474c50683b3455d50e11ab2`.
- Merged through PR #93; merge commit: `5b9ca7c3272ffb09a4f77fab3d58e1cafc52d36d`.
- `uv sync --extra dev`: passed.
- Focused command (with the renamed integration test module): **12 passed**.
- `uv run ruff check .`: passed, all checks clean.
- `uv run pytest`: **545 passed** across 55 test files; 4 pre-existing librosa/audioread deprecation warnings.
- `git diff --check base..HEAD`: passed.
- Changed files: exactly the nine M18.3 files listed in PR #93.
- Candidate validation worktree: clean at the exact SHA.
- Original checkout preservation: branch `feat/m12-5-recommendation-retrieval`, HEAD `8185080929b87f25c962639574abafbf887cb455`, same 75 pre-existing modified paths, and empty stash before/after.
- The original validation worktree at the failing candidate was preserved; a separate sibling worktree validated the corrected candidate. No GitHub Actions/CI was used.

The earlier candidate `371baecaa7349c0f53f8cc72a82b7d9173c93b02` failed collection because the unit and integration test modules shared a basename. Renaming the integration test to `tests/integration/test_listening_summary_integration.py` fixed collection without changing pytest configuration. The corrected combined focused command and full suite both passed.
