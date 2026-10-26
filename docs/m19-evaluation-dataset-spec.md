# M19 Evaluation Dataset Specification

## Purpose

Define the fixed, reviewable ground truth that [M19](m19-recommendation-quality-evaluation-contract.md) metrics are computed against, and the rules that keep private music data out of the repository.

## Design principles

1. **Small and inspectable** — a person can read the whole set and re-judge it.
2. **Hand-judged** — every grade is assigned by a person. Trusted catalog metadata may serve as evidence, but no grade is derived by a script.
3. **Unknown is not negative** — an unjudged track is not an irrelevant track.
4. **Private data never committed.**
5. **Frozen per version** — a metric difference across major versions is not a comparison.
6. **Independent of system identity** — judgments are made without knowing which system produced a track, its rank, or its score.

## Two-tier layout

Tier 1 — committed to the repository:

```text
datasets/m19/
  README.md                how to judge and how to version
  queries-v1.json          the query set
  judgments.example.json   worked example of the judgment file shape
```

Operational walkthrough and query-set entry point: [datasets/m19/README.md](../datasets/m19/README.md).

Tier 2 — local only, ignored by git:

```text
data/eval/
  judgments.local.json     real judgments against your own catalog
  reports/                 generated reports
```

The implementation slice adds `data/eval/` to `.gitignore`. Nothing under `data/eval/` may be committed, and `git status` must show no trace of it.

### Three classes, never conflated

| Class | Path | In git? | Contents |
|---|---|---|---|
| Query definitions | `datasets/m19/queries-v1.json` | **committed** | generic requests, facets, notes |
| Real judgments | `data/eval/judgments.local.json` | **ignored** | your catalog's track ids and grades |
| Reports | `data/eval/reports/` | **ignored by default** | metrics and provenance |

A synthetic `judgments.example.json` is the only judgment-shaped file that is committed, and it must contain fabricated track ids only.

### Pre-write privacy gate (mandatory)

Before writing any real judgment file **or** report, confirm that **both** expected paths are ignored:

```bash
git check-ignore -v data/eval/judgments.local.json
git check-ignore -v data/eval/reports/baseline-report.json
```

Both must report an ignore rule. If either returns nothing, **stop before the first write**. Add the rule, then re-run both checks. A judgment run must never leave real track identifiers, filenames, or paths visible to `git status`. This check precedes the first write, not the commit.

Reports may be committed only after confirming they carry no personal track identifiers, no filenames, no listening-event contents, and no absolute filesystem paths. Default is local.

## Query record schema

```json
{
  "id": "q001",
  "text": "high energy cinematic hero entry",
  "facets": {
    "genre": ["cinematic"],
    "mood": ["heroic"],
    "energy": "high"
  },
  "context": "coding",
  "notes": "expects a driving orchestral opening cue"
}
```

- `id` is stable across dataset versions.
- `text` is the literal string passed to retrieval.
- `facets` documents what the judge expects. It is explanatory only and must never be used as an automatic relevance label.
- `context` is optional and used only by the personalization and context-isolation slice.
- `notes` is free text and must contain no private identifiers.

**Size:** 20–40 queries for v1, target 30. Cover the facets that actually matter, then list uncovered facets in the limitations block rather than implying coverage that does not exist.

## Judgment record schema

```json
{
  "dataset": "m19-queries",
  "dataset_version": "1.0.0",
  "catalog_fingerprint": "sha256:…",
  "judged_at": "2026-10-26T00:00:00Z",
  "judgments": [
    { "query_id": "q001", "track_id": "abc123", "grade": 3, "reason": "driving orchestral open" },
    { "query_id": "q001", "track_id": "def456", "grade": 0, "reason": "ambient pad, no build" }
  ]
}
```

### Relevance scale

| Grade | Meaning |
|---|---|
| 3 | Strong match — would confidently recommend for this request |
| 2 | Relevant — fits the request, acceptable to surface |
| 1 | Marginal — related, but would not satisfy the request |
| 0 | Known mismatch — judged and confirmed not to fit |
| *(absent)* | Unjudged — never scored, excluded from every metric |

**Grade 0 and absent are different things.** An explicit `0` means "I checked and it does not fit." Absent means "I never checked." Ranking metrics must exclude absent entries rather than reading them as `0`.

### Judging procedure

1. Build the **frozen pool**: for each query, take the distinct union of the top 10 results from every mode being compared — `catalog`, `lexical`, `semantic`, `hybrid` where available — deduplicated.
2. Record **pool provenance**: dataset version, retrieval modes compared, candidate limit per mode, and the ordered top-10 results used to construct the pool.
3. **Shuffle**, so the judge cannot see which system produced a track, nor its rank.
4. Listen or inspect, then assign 0–3 with a one-line reason.
5. Record pool members by track ID; a track in the frozen pool without a judgment is **distinguishable** from a track that was never retrieved by any compared mode.
6. The query's pool is complete only when **every** track in it carries a judgment. The pool is frozen with the dataset version: adding a mode, changing the candidate limit, or changing pool depth alters the pool and requires a version change.
7. **The evaluator must return `not_evaluable` when a run returns tracks outside the recorded frozen pool.** A track outside the pool is not a judgment of any kind; it is a pool-violating result.
8. The evaluator must not remove unjudged tracks or compress ranks to make a pool appear complete.

### Pre-write privacy gate (mandatory)

Before writing any real judgment file **or** report, confirm that **both** expected paths are ignored:

```bash
git check-ignore -v data/eval/judgments.local.json
git check-ignore -v data/eval/reports/baseline-report.json
```

Both must report an ignore rule. If either returns nothing, **stop before the first write**. Add the rule, then re-run both checks. A judgment run must never leave real track identifiers, filenames, or paths visible to `git status`. This check precedes the first write, not the commit.

Reports may be committed only after confirming they carry no personal track identifiers, no filenames, no listening-event contents, and no absolute filesystem paths. Default is local.

**Do not add `.gitignore` rules in this documentation review phase.** Record that the evaluator implementation must add and verify the rules before any real judgment or report write.

### Evidence rules — what a grade may rest on

Independence is required from **system outputs**, not from evidence about the music.

A grade must **not** be based on:

- the ranker's score, weights, or fusion output;
- which system or retrieval mode produced the track;
- the track's position in the ranked list;
- the retriever's match trace or explanation for why it surfaced.

A grade **may** be based on:

- listening to the audio;
- catalog metadata the judge trusts — genre, artist, album, year, tempo, language;
- the query text itself.

The circularity rule is narrow: the *retriever's own match trace* may not be the justification. "Relevant because the retriever matched `genre=cinematic`" is not an acceptable reason. "Relevant — I listened; it is cinematic orchestral with a building open" is acceptable even if genre metadata was among the evidence consulted. The test is whether the grade states an independent musical observation rather than echoing the system's decision.

### Judging independence — how blindness is enforced

The pool is shuffled before judging, and the judge's view must not include system identity, rank, or score. Because pooling merges several modes, the same track can appear for multiple queries; grade it per query, not once globally.

### Coverage requirements — complete-pool

Official metrics require a **fully judged frozen pool**. The exact rule lives in the [contract's metric definitions](m19-recommendation-quality-evaluation-contract.md); in summary:

1. every track in the query's frozen pool must carry a judgment;
2. at least 3 tracks in the pool must carry a judgment;
3. `Recall@10` additionally needs ≥ 1 judged-relevant track in the pool;
4. `nDCG@10` additionally needs `IDCG@10 > 0`.

A query that fails is reported as `not_evaluable` with the precise failing condition as its reason — for example `pool incomplete: 2 of 9 pooled tracks unjudged` — never as a score, and never silently dropped from the totals.

- Report judged ÷ pooled per query and overall as `pool coverage`; official metrics require it to be complete.
- Report `evaluable / total` query counts and gate-failure counts by reason beside every ranking metric.
- **Pooling bias is expected and must be stated:** tracks retrieved by no compared system are unjudged by construction, and no compared system is credited for a track outside its own pool. This limitation belongs in every report.
- The gate may only be made stricter by an explicit contract amendment; it must not be relaxed per run to raise the number of evaluable queries.
- The gate is identical for `nDCG@10`, `Recall@10`, and `MRR@10`. It is never relaxed for one metric.

## Stability and versioning

Dataset versions use `MAJOR.MINOR.PATCH`:

- **PATCH** — typo and note fixes; no grade changes.
- **MINOR** — new queries, or new judgments appended to existing queries.
- **MAJOR** — any grade change, any change to query text, or any change to a frozen pool (adding a mode, changing the candidate limit, or changing pool depth).

Metrics are never compared across MAJOR versions.

`catalog_fingerprint` hashes the catalog identity used to produce judgments (track ids plus content hashes). If the local catalog changes materially, re-judge or bump MAJOR; a report referencing a stale fingerprint is marked non-reproducible rather than quietly reported.

**A `catalog_fingerprint` is provenance, not anonymity.** It ties a report to the catalog revision that produced it. It does not conceal track identity and must never be presented or relied upon as a privacy safeguard.

Every report records the dataset version and the SHA-256 of the judgment file it consumed.

### Pool-expansion workflow

The pool-expansion workflow ensures fair comparison across dataset versions:

1. **Extend and re-judge the pool**: explicitly add new modes or adjust the candidate limit, then re-judge every track in the expanded pool.
2. **Bump the dataset version** (MAJOR) as required by the existing versioning rules.
3. **Compare baseline and candidate** on the same updated dataset version, ensuring a fair comparison on the same frozen pool.
4. Record the new pool manifest alongside the report so the pool definition is auditable and reproducible.

## Deferred: personalization holdout slice (not Phase 1)

This slice is out of scope for the initial baseline. It is retained here so the design is not lost, and becomes binding only if the contract is amended to promote it into a later phase.

Separate from the ranking dataset:

- Order listening events by timestamp; default split holds out the final 20%, recorded in the report.
- Build recommendations only from events strictly before the cutoff; score against events at or after it.
- Evaluate each context separately; contexts are never mixed.
- A leakage guard test asserts that injecting a post-cutoff event does not alter a pre-cutoff recommendation.

Playlist diagnostics are likewise deferred; see the contract's deferred phase notes.

## Limitations block (required in every report)

Every report copies this block verbatim. It is not optional and may not be abbreviated.

**Scale limits:**

- The query set is small (target 30). A single query can move a macro-average materially, so treat small deltas between runs as noise, not signal.
- No confidence interval is computed and no significance test is claimed at this size.
- Facet coverage is partial; uncovered facets are listed explicitly rather than assumed to generalize.

**Judge limits:**

- One judge, one listener. There is no inter-rater agreement to report and no cross-listener generalization.
- Grades reflect that listener's taste and reading of the query text.
- Grading is human and slow, so the judged fraction is partial by design.

**Pooling limits:**

- The pool is the union of top-10 results from the compared modes, so tracks no mode retrieved are unjudged by construction.
- Pooled recall is relative to the judged pool, not the corpus. It is not comparable to corpus-wide recall.
- A system outside the pool gets no credit for relevant-but-unjudged tracks.

**Metadata limits:**

- Judgments may lean on catalog metadata, which is itself incomplete; unknown attributes are recorded as unknown, not inferred.
- Whether optional semantic or hybrid modes were available when judgments were made is stated, since an unavailable mode narrows the pool.

## Privacy rules

**Pre-write gate:** the mandatory two-command check in [Pre-write privacy gate](#pre-write-privacy-gate-mandatory) must report an ignore rule for **both** the judgment path and the report path before the first write of either file. If either returns nothing, stop.

Never commit:

- artist, album, title, filename, or file paths drawn from a private library;
- real track identifiers from a private catalog, in examples or reports;
- listening-event contents;
- reports containing any of the above;
- absolute filesystem paths of any kind.

Committed queries are generic music requests, not transcriptions of local filenames. The committed `judgments.example.json` uses fabricated track ids only.

A `catalog_fingerprint` is **provenance, not anonymity** — it ties a report to the catalog revision that produced it; it does not hide track identity.

## Worked example

A minimal complete dataset with one query and two judgments:

```json
{
  "dataset": "m19-queries",
  "dataset_version": "1.0.0",
  "catalog_fingerprint": "sha256:4f2c…",
  "judged_at": "2026-10-26T00:00:00Z",
  "judgments": [
    { "query_id": "q001", "track_id": "t-a", "grade": 3, "reason": "driving orchestral open" },
    { "query_id": "q001", "track_id": "t-b", "grade": 2, "reason": "steady build, fits cue" }
  ]
}
```

Track `t-c` is absent from this file for `q001`, so it was never judged.

- If `t-c` is **not** in `q001`'s frozen pool, its absence is expected and the pool can still be complete.
- If `t-c` **is** in `q001`'s frozen pool, the pool is incomplete: `q001` is `not_evaluable` with a reason such as `pool incomplete: 1 of 3 pooled tracks unjudged`, and contributes to no official metric.

In neither case is `t-c` read as grade `0`. The evaluator never removes an unjudged track and never compresses result ranks.

## Change control

The specification and the committed dataset land with the contract. Changing grades, query text, or a frozen pool after a baseline exists requires a MAJOR version bump and an entry in the [milestone ledger](milestone-status.md), because the old and new results are no longer comparable.

This specification is intentionally a separate, independently versioned document: its schema and pool definition may change without editing the milestone contract.
