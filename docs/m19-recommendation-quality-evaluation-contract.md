# M19 — Recommendation Quality Evaluation Baseline

## Purpose

Establish a small, inspectable, repeatable local process that measures whether SoundMind retrieves and ranks relevant music, so that later changes to ranking, retrieval, or models can be compared against a recorded baseline instead of asserted to be improvements.

This contract defines the evaluation boundary and its dataset. It changes no recommendation behavior.

## Document set

M19 is documented in two files that are deliberately separate:

- **This contract** — the milestone boundary, metric definitions, phasing, report contract, and acceptance criteria. It changes only when the milestone's scope or semantics change.
- **[M19 evaluation dataset specification](m19-evaluation-dataset-spec.md)** — the record schemas, judging rubric, coverage rules, and versioning policy. Its schema and `MAJOR.MINOR.PATCH` version can evolve independently of this contract, so a dataset revision does not require editing milestone scope.

Do not merge them; a dataset format change is not a contract change.

## Baseline

Base: `main` at `0a62535e269bb0d41ffb3986df30dcf61ba42274`.

Reuse unchanged: catalog-backed candidate generation, the M12 retrieval modes, M1 fusion, M2 sequencing, the M11/M18 CLI boundaries, and the SQLite catalog plus listening-event store.

The evaluator is a read-only consumer of these surfaces. It must not reimplement ranking, and it must not write to catalog, playlist, or listening-event state.

## Status

Contract only. No evaluator, dataset, baseline report, or metric implementation exists in the repository tree at this revision. No validation result is claimed for M19 here; validation status may be recorded only after an implementation candidate has actually passed its local gate.

## Scope

### Phases

The first runnable baseline is deliberately narrow.

**Phase 1 (this contract's acceptance): retrieval/ranking metrics and judgment coverage.** The immediate question is whether the retriever surfaces relevant music and ranks it well. That is answerable from a judged query set alone and does not depend on listening history or sequencing.

**Phase 2 (deferred): personalization holdout.** Requires a mature, time-ordered listening-event history and a leakage guard; it answers a different question — whether feedback improves later results — and cannot be measured until the query set and Phase 1 metrics are stable.

**Phase 3 (deferred): playlist diagnostics.** Sequencing operates downstream of retrieval and ranking. Measuring it before the ranking baseline exists would attribute a sequencing outcome to a retrieval change, so it waits for a stable Phase 1.

Phases 2 and 3 are retained below as design notes, not as Phase 1 deliverables, and no Phase 1 acceptance criterion depends on them. They may be promoted into scope later only by an explicit contract amendment that states why the initial baseline requires them.

### Deliverables (Phase 1)

1. **Evaluation dataset** — defined by the [M19 evaluation dataset specification](m19-evaluation-dataset-spec.md).
2. **Evaluator** — a local command that runs a fixed query set through a chosen retrieval mode, computes ranking metrics, and writes a report.
3. **Ranking metric implementations** — nDCG@10, Recall@10 (pooled), and MRR@10, each with unit tests and defined behavior for empty, unjudged, incompletely pooled, and insufficiently covered input.
4. **Judgment coverage reporting** — per-query and aggregate coverage, with the `not_evaluable` gate described below.
5. **Baseline report** — a versioned record of results for every supported mode at the first measured revision.

### Measurement surfaces (Phase 1)

| Surface | What it answers | Metrics |
|---|---|---|
| Retrieval and ranking | Are the right tracks found, and placed high? | nDCG@10, Recall@10 (pooled), MRR@10 |
| Judgment coverage | Was the frozen pool judged completely? | pool coverage, evaluable query counts, gate-failure reasons |
| Catalog coverage | How much of the catalog is reachable, and how often is evidence missing? | candidate-pool coverage, missing-evidence rate |

Deferred to later phases: personalization (held-out preference ordering, contextual isolation) and playlist sequencing (repeated-track rate, energy-trajectory deviation, transition-feature continuity).

### Metric definitions

All three metrics are computed per query and macro-averaged across **evaluable** queries only. A query that fails any gate below is reported as `not_evaluable` with a reason and contributes to no average.

#### Frozen judgment pool

Each compared retrieval mode returns its own top 10 for a query. The query's **frozen pool** is the distinct union of those tracks, deduplicated.

The pool is frozen for a dataset version. Adding a mode, changing the candidate limit, or changing pool depth alters the pool and therefore requires a dataset version change. The pool — not the catalog and not the corpus — is the unit of judging and of evaluability.

### Pool provenance

- **Pool members** are identified by their track ID and their exact position in the returned top-10 results.
- **Pool provenance** records the dataset version, retrieval modes compared, candidate limit per mode, and the ordered top-10 results used to construct the pool.
- A track that appears in the frozen pool but has no judgment is **distinguishable** from a track that was never retrieved by any compared mode.
- The evaluator must return `not_evaluable` when a run returns tracks outside the recorded frozen pool.

### Pool-expansion workflow

1. **Extend the pool**: explicitly add new modes or adjust the candidate limit.
2. **Bump the dataset version** (MAJOR) as required by the existing versioning rules.
3. **Re-judge the pool**: every track in the expanded pool must be re-judged.
4. **Compare baseline and candidate** on the same updated dataset version, ensuring a fair comparison on the same frozen pool.

#### Relevance threshold

A track is **relevant** exactly when its grade is `≥ 2`. Grades `2` and `3` are relevant; grades `0` and `1` are not. This single threshold governs both `Recall@10` and `MRR@10`. `nDCG@10` uses all four grades rather than the threshold.

#### nDCG@10 gain calculation

```
gain(g)  = 2^g - 1                  for grade g in {0,1,2,3}
             → gains: 0→0, 1→1, 2→3, 3→7

DCG@10   = Σ_{i=1..10} gain(g_i) / log2(i + 1)     (i is 1-based original rank)
IDCG@10  = Σ_{i=1..m}   gain(g'_i) / log2(i + 1)
             where g' = the ten highest judged grades in the frozen pool,
                        sorted descending
             and m   = min(10, frozen-pool size)

nDCG@10  = DCG@10 / IDCG@10
```

**Gain:** `2^grade - 1` for grades 0–3, giving 0, 1, 3, 7. Gain is computed once and reused by both sums.

**Fewer than ten eligible items:** `m = min(10, frozen-pool size)`, so a pool of 6 sums the six highest judged gains at positions 1–6. A pool smaller than ten is not padded with zeroes and is not by itself a failure.

**Define DCG@10 precisely** (short-list definition):
- DCG@10 is computed over `min(10, returned result count)` actual result positions.
- Do not pad the returned list with invented tracks.
- For diagnostic calculations only, an unjudged result has zero gain at its original rank, and no rank compression is permitted.
- Keep official incomplete-pool metrics `not_evaluable`.
- Keep IDCG based on the highest judged grades in the frozen pool, using the existing `m = min(10, frozen-pool size)` rule.

**Original ranks are preserved:** unjudged tracks remain in their returned position and contribute `gain = 0`. Nothing is removed and no rank is compressed — rank compression would silently inflate DCG by moving good results closer to rank 1. The metric implementation must preserve original ranks and carry an explicit test for unjudged-item handling.

**Incomplete pools are `not_evaluable` for official comparisons.** If any pooled track lacks a judgment, the query contributes no official `nDCG@10`. The implementation may still compute a diagnostic value, but official reports exclude it.

#### Recall@10 (pooled, not corpus-wide)

```
Recall@10 = |{ relevant tracks in the returned top-10 }|
            ------------------------------------------------
            |{ judged-relevant tracks in the frozen pool }|
```

- The denominator is the **judged-relevant items in this query's frozen pool**, never the corpus. Recall against a full catalog is not defined here and must not be reported.
- Because the denominator is pool-relative, a system is credited only for relevant tracks that some compared mode already retrieved. Tracks no mode retrieved are unjudged by construction; that is a known property of pooled evaluation and belongs in the dataset limitations.
- Unjudged tracks in the top-10 stay in position and count as not-relevant-for-this-computation, subject to the gate — they are not treated as judged-irrelevant, and they are not dropped.
- If the pool contains zero judged-relevant tracks for the query, the query is `not_evaluable` for Recall (division by zero), not `0` and not `1`.

#### MRR@10

```
MRR@10 = 1 / (original position of the first top-10 result with grade ≥ 2)
       = 0 when no top-10 result has grade ≥ 2
```

- A result is relevant at grade `≥ 2`, and only the **first** relevant result among the original top-10 positions contributes reciprocal rank.
- Positions are the original returned positions. No track is removed and no rank is compressed to find that first result.
- `MRR@10` is subject to the **same** evaluability gate as `nDCG@10` and `Recall@10`; the gate is never relaxed for MRR. A `0` is reported only for a fully judged pool. An incomplete pool yields `not_evaluable`, not `0`.

#### Evaluability gate — complete-pool coverage

Official metrics require a **fully judged frozen pool**. The earlier fractional `coverage@10 ≥ 0.5` threshold is withdrawn and replaced by complete-pool coverage.

A query contributes official metrics only when **all** of the following hold. Otherwise every metric for that query is reported as `not_evaluable`, with the precise failing condition as its reason:

1. **Complete-pool coverage** — every track in the query's frozen pool carries a judgment. One unjudged pooled track fails the query. The reason states the counts, for example: `pool incomplete: 2 of 9 pooled tracks unjudged`.
2. **Minimum-size guard** — at least 3 tracks in the pool carry a judgment, retained as an additional guard against trivially small pools.
3. **`Recall@10`** — at least 1 judged-relevant track in the pool.
4. **`nDCG@10`** — `IDCG@10 > 0`.

5. **No tracks outside the frozen pool** — if the evaluator returns any track not in the recorded frozen pool, the query is `not_evaluable` with reason `pool: returned tracks outside frozen pool`.

These conditions are contract-level. They may be tightened only by an explicit amendment, and must not be relaxed per run to increase the number of evaluable queries.

Unjudged tracks are never removed from a ranked list and result ranks are never compressed, whether or not the query passes the gate. A dedicated test asserts both.

### Pool-expansion workflow

The pool-expansion workflow ensures fair comparison across dataset versions:

1. **Extend and re-judge the pool**: explicitly add new modes or adjust the candidate limit, then re-judge every track in the expanded pool.
2. **Bump the dataset version** (MAJOR) as required by the existing versioning rules.
3. **Compare baseline and candidate** on the same updated dataset version, ensuring a fair comparison on the same frozen pool.
4. Record the new pool manifest alongside the report so the pool definition is auditable and reproducible.

#### Reporting rules

- If no query is evaluable, the metric is reported as `null` with a reason, never as `0` or `1`.
- Every macro-averaged metric is accompanied by `evaluable / total` query counts, plus gate-failure counts broken down by reason.
- `pool coverage` (judged ÷ pooled) is reported per query and overall even though official metrics require it to be complete; the shortfall shows how much candidate work went unjudged.
- Unjudged tracks are never scored as irrelevant and never removed from the ranked list.

#### Coverage (reported separately from quality)

Reported alongside metrics so a strong score over a thin pool cannot look like broad capability:

- `pool coverage` — judged tracks ÷ frozen-pool tracks, per query and overall; official metrics require 1.0.
- `candidate-pool coverage` — returned candidates ÷ active catalog size.
- `missing-evidence rate` — share of returned candidates lacking evidence for a requested facet, using the "unknown ≠ negative" rule from the [product roadmap](product-roadmap.md).

### Deferred phase notes

These are design notes for later phases and are **not** part of the Phase 1 baseline.

**Phase 2 — personalization holdout:**

- Listening events ordered by timestamp; default split holds out the final 20%, recorded in the report.
- Recommendations generated only from events strictly before the cutoff, scored against events at or after it.
- Each context evaluated separately; events from context B never influence a result evaluated in context A.
- An automated leakage guard asserts that injecting a post-cutoff event does not alter a pre-cutoff recommendation.

**Phase 3 — playlist quality** (measurable proxies, explicitly not listener preference):

- `repeated-track rate` — share of entries whose track appears more than once.
- `energy-trajectory deviation` — mean absolute difference between the requested arc and observed normalized energy, position-aligned; only for modes with a requested arc (for example Journey).
- `transition-feature continuity` — mean absolute consecutive-track delta of a normalized feature, reported against a reference ordering.

### Report provenance

Every report records:

- dataset id, dataset version, and SHA-256 of the judgment file;
- code revision (candidate SHA);
- retrieval mode and candidate limit;
- fusion weights actually used;
- optional model/index configuration — model name, index path, index freshness state, and query-expansion setting;
- UTC timestamp, Python version, and platform;
- unavailable optional modes, each with its reason;
- per-metric `evaluable / total` query counts and gate-failure counts by reason;
- the dataset's limitations block, copied verbatim (see the specification).

Determinism: the same dataset, configuration, and revision must produce identical metric values; only the timestamp may differ.

### Data classification

Three classes of evaluation data exist and must never be conflated:

| Class | Path | In git? | Contents |
|---|---|---|---|
| Query definitions | `datasets/m19/queries-v1.json` | **committed** | generic requests, facets, notes |
| Real judgments | `data/eval/judgments.local.json` | **ignored** | your catalog's track ids and grades |
| Reports | `data/eval/reports/` | **ignored by default** | metrics and provenance |

**Pre-write privacy gate (mandatory):** before the first write of any real judgment file or report, confirm that **both** expected paths are ignored:

```bash
git check-ignore -v data/eval/judgments.local.json
git check-ignore -v data/eval/reports/baseline-report.json
```

Both must report an ignore rule. If either returns nothing, **stop before the first write** — add the rule, then re-run both checks. A judgment run must never leave real track identifiers, filenames, or paths visible to `git status`.

Reports may be committed only after confirming they contain no personal track identifiers, no filenames, no listening-event contents, and no absolute filesystem paths. Default is local.

A `catalog_fingerprint` is **provenance, not anonymity.** It records which catalog produced the judgments so a report can be tied to a data revision; it does not conceal track identity, and it must not be treated as a privacy safeguard.

No network access, cloud scoring, or paid API is involved in any part of M19.

### CLI contract (proposed shape)

```text
soundmind eval run --dataset PATH --judgments PATH --retrieval MODE --limit N --out PATH
soundmind eval compare --baseline PATH --candidate PATH
```

- `--retrieval` accepts the existing modes: `catalog` (default), `lexical`, `semantic`, `hybrid`, `hybrid-indexed`.
- A mode whose optional dependency, model, or index is unavailable is reported as `unavailable` with a reason rather than silently skipped.
- The command is read-only with respect to catalog, playlist, and listening-event state.
- The command exits non-zero if the dataset fails schema validation.

The exact flag names are provisional and may change during implementation without altering this contract's measurement semantics.

### Non-goals

- No change to ranking weights, fusion weights, retrieval scoring, or sequencing behavior in this milestone.
- No newly required model, dependency, or cloud service; optional modes remain optional.
- No claim that a metric equals listener satisfaction; playlist metrics are proxies, and they are out of Phase 1 entirely.
- No automatic relevance labeling; judgments are human. Trusted catalog metadata may serve as judging evidence (see the rubric in the specification), but no label is derived by a script.
- No leaderboard, target percentage, or improvement promise before a baseline exists.
- No corpus-wide recall, no personalization evaluation, and no playlist diagnostics in Phase 1.
- No new playlist commands, import/export formats, or catalog schema changes.

## Validation gate

When an implementation candidate exists, run on the exact candidate SHA in an isolated worktree:

```bash
uv sync --extra dev
uv run pytest tests/unit/eval tests/integration/test_eval_report.py
uv run ruff check .
uv run pytest
git diff --check 0a62535e269bb0d41ffb3986df30dcf61ba42274..HEAD
git diff --name-only 0a62535e269bb0d41ffb3986df30dcf61ba42274..HEAD
git status --short --branch
```

Record exact base/candidate SHAs, focused and full test counts, Ruff and diff-check exit codes, changed-file scope, dataset version and hash, coverage figures, and confirmation that the original checkout remains unchanged. Do not record validation status until the gate has actually passed.

## Acceptance

M19 Phase 1 is complete when:

1. one documented local command reproduces a report for a fixed dataset and configuration, with identical metric values across runs;
2. nDCG@10, pooled Recall@10, and MRR@10 each have unit tests covering empty input, all-unjudged input, zero-relevant-pool input, pools under ten items, `IDCG@10 = 0`, and incomplete-pool gate failure;
3. the gate marks any query with an unjudged pooled track `not_evaluable`, naming the unjudged count, and emits `null` with a reason whenever no query is evaluable;
4. the report covers all supported retrieval modes and explicitly lists unavailable optional modes with reasons;
5. unjudged tracks are never scored as irrelevant and are never removed to compress ranks, asserted by a dedicated test;
6. the pre-write privacy gate is documented and **both** the judgment path and an expected report path are verified ignored before the first write;
7. the dataset's limitations block — including small size, single judge, and pooled construction — appears verbatim in every report;
8. the full local Ruff + pytest gate passes on the exact candidate SHA;
9. no ranking or fusion weight changed in the candidate diff.

Personalization and playlist metrics are explicitly not acceptance criteria for Phase 1.
