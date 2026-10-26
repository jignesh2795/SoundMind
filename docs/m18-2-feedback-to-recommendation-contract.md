# M18.2 — Feedback-to-Recommendation End-to-End Proof

## Purpose

Prove that listening feedback recorded through the M18.1 CLI and persisted in SQLite is consumed by the existing catalog-backed recommendation path, and that the resulting preference signal reaches the existing ranking boundary. This is a test-first integration milestone, not a new recommendation algorithm.

## Baseline

Base: `main` at `ff9a2c7e8c63aa8079407d68dcdbee4ffbd32a9d`.

Reuse the existing:
- `soundmind event add` and `soundmind event list` CLI commands;
- `ListeningEventRepository` and SQLite listening-event table;
- `CatalogContextRecommendationService`;
- `ContextAwareMusicFlow`, M9 contextual preference, M10 contextual novelty, M1 ranking, and M2 sequencing;
- deterministic reference-time and context contracts.

M18.1 already proves real-SQLite event capture/listing and that captured events can be scored by the global and contextual preference scorers. M18.2 closes the remaining observable integration gap: prove the persisted feedback reaches the application-facing recommendation result without bypassing existing boundaries.

## Scope

Add integration-level regression coverage using a temporary SQLite database and deterministic timestamps. Prefer the existing public CLI/service boundaries over direct private-function calls.

At minimum, tests should establish:

1. A feedback event recorded through the CLI is persisted and later read by the catalog-backed recommendation service from the same database.
2. A contextual event contributes only to its matching context; unrelated contexts remain isolated.
3. The recommendation path receives the existing preference signal while preserving signal ownership and the existing M1 fusion weights.
4. Repeating the same request with identical database state, context, reference time, limits, and dependencies produces deterministic results.
5. No production behavior change is needed merely to make a test pass; if a real defect is exposed, implement the smallest fix at the owning boundary and add a targeted regression test.
6. Tests use local fixtures and temporary SQLite only; no personal music library, model download, external service, network access, or paid API is required.

## Non-goals

- No new event types, schema, migration, or dependencies.
- No new recommendation algorithm, score weights, preference decay, or ranking changes.
- No automatic context inference or background collection.
- No UI, streaming integration, cloud service, or LLM requirement.
- No benchmark claims or assertions that a preference event must always change the final top track when other ranking signals legitimately dominate.

## Validation gate

Run on the exact candidate SHA in an isolated worktree:

```bash
uv sync --extra dev
uv run pytest <focused-new-and-related-integration-tests>
uv run ruff check .
uv run pytest
git diff --check
git status --short
```

Record the exact candidate/base SHAs, focused and full test counts, Ruff result, diff-check result, exact changed-file scope, and confirmation that the original checkout is unchanged. Do not update validation status until the local gate actually passes.

## Acceptance

M18.2 is complete when:
- the CLI-to-SQLite-to-recommendation path is covered end to end;
- context isolation and deterministic reference-time behavior are directly asserted;
- existing signal ownership and ranking weights remain unchanged;
- the normal local Ruff + pytest gate passes on the exact candidate SHA;
- the PR is limited to the contract-driven test/fix scope and does not trigger GitHub Actions.
