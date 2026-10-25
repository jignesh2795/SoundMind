# M18.1 — Listening Feedback Capture

## Purpose

Expose the existing persisted listening-event and preference-scoring infrastructure through a minimal local CLI, so users can record the feedback that recommendations already know how to consume.

## Baseline

Designed from `main` at `ebb2d13dfbce9fa2f0eabc731f537fe0cd96f4c8`.

Existing contracts reused:

- `ListeningEvent` and `ListeningEventType` in `soundmind.preferences.models`;
- `ListeningEventRepository` and the existing `listening_events` SQLite table;
- `TrackRow` catalog identity;
- `PreferenceScorer` and `ContextualPreferenceScorer`;
- the CLI's existing timezone-aware `_parse_now` and `--db` convention.

No schema migration or new dependency is required.

## CLI contract

### Add one event

```text
soundmind event add TRACK_ID TYPE [--at ISO-8601] [--context TEXT]
    [--seconds-played FLOAT] [--db PATH]
```

Supported types are exactly `play`, `complete`, `skip`, `like`, `dislike`, and `replay`. Argparse rejects any other type.

- `TRACK_ID` must identify an existing `TrackRow`. The row may be active or inactive; inactive status must not erase valid historical listening.
- Missing or blank IDs raise `KeyError("Track not found: ...")`, matching existing strict track-lookup conventions.
- `--at` uses the existing timezone-aware ISO-8601 parser. Accepted times are normalized to UTC; if omitted, the repository's UTC-now path is used.
- `--context` is stored as supplied when nonblank. A whitespace-only context is normalized to `None`. Context is not lowercased or stripped on write.
- `--seconds-played` is optional and must be finite and non-negative. Booleans are rejected by the application helper. It is stored as event evidence only; current scorers do not consume it.
- A successful add commits exactly one event and prints its recorded timestamp and fields.

### List recent events

```text
soundmind event list [--limit N] [--db PATH]
```

Default limit is 20. The existing repository's positive-limit validation remains authoritative. Events are listed newest first using the existing repository order.

Each output row is tab-delimited with five stable columns:

```text
UTC_TIMESTAMP<TAB>TYPE<TAB>TRACK_ID<TAB>CONTEXT<TAB>SECONDS_PLAYED
```

Absent context or playback duration is represented by an empty column. Tabs, carriage returns, and newlines embedded in context are escaped in the printed value so each event remains one output line. Empty history prints `No listening events.`.

## Application boundary

`soundmind.listening` exposes two thin application helpers:

- `record_listening_event(...)`: validate the catalog reference and event inputs, normalize the timestamp/context boundary, and delegate persistence to `ListeningEventRepository`;
- `list_listening_events(...)`: delegate ordered history retrieval and limit validation to the existing repository.

The module does not duplicate persistence behavior. CLI output is formatting only; preferences continue consuming the existing `ListeningEvent` objects.

## Non-goals

- No database schema change or migration.
- No change to preference weights, half-life, ranking, novelty, retrieval, or sequencing.
- No event editing, deletion, undo, listening-session aggregation, or bulk/history import.
- No web UI, external API, cloud dependency, new ML model, or dependency addition.
- No enforcement of `TrackRow.status == "active"` for event capture.

## Tests and validation gate

Required coverage includes:

- existing inactive versus missing/blank catalog IDs;
- valid and invalid event types;
- timezone normalization and rejection of naive timestamps;
- finite/non-negative playback duration checks;
- whitespace-only context normalization without modifying nonblank context;
- default UTC time and list-limit forwarding/validation;
- CLI parser, dispatch, output, empty history, and argument defaults;
- a real temporary-SQLite CLI add/list round-trip;
- proof that recorded events feed the existing global and contextual preference scorers;
- proof that a missing track cannot create an event.

The implementation branch must be checked on its exact candidate SHA with:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest
git diff --check
git status --short
```

Validation status remains pending until those commands are run on the exact candidate SHA. The M17.6 baseline was Ruff clean with 516 tests passing.
