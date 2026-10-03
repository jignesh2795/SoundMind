# M17.6 — Historical Validation Branch Hardening

## Purpose

M17.6 closes remaining validation-branch gaps in the historical M2/M3/M4/M6/M10/M11 layers. The slice is test-focused: strengthen regression protection around documented rejection, empty/fallback, determinism, immutability, and boundary behavior without changing product behavior.

## Scope

The target historical layers are:

- M2 sequence engine;
- M3 MusicIntent parser;
- M4 intent-aware retrieval;
- M6 SQLite catalog adapter/pipeline;
- M10 contextual novelty and context-aware composition;
- M11 catalog-backed recommendation and its CLI/application boundary.

The implementation should add targeted tests where the current suite does not already protect a documented contract. Existing positive-path tests should not be duplicated merely for count.

## Required audit method

For each target layer:

1. read the milestone contract and current production boundary;
2. identify a concrete contract branch not already protected;
3. add the smallest deterministic regression test;
4. where practical, perform a fail-first mutation against the exact guarded behavior and verify the new test goes RED;
5. restore production code unchanged before final validation.

Tests must use local fakes/stubs where external filesystem, ML, or service boundaries are involved.

## Target behaviors

### M2 — sequence engine

Prioritize boundary cases not already covered:

- invalid positive-limit typing, including `bool`;
- optional feature validation (`energy`, `tempo_bpm`, `brightness`, `novelty_score`);
- missing optional sequencing features remaining valid;
- non-finite feature rejection beyond `base_score`;
- unknown sequence mode rejection at the actual request boundary;
- missing seed rejection and deterministic seed-first behavior;
- empty candidate handling and input immutability where a branch is currently uncovered.

### M3 — MusicIntent parser

Prioritize constructor/parser validation and normalization branches:

- invalid `energy` and `confidence` construction boundaries;
- invalid `vocal_preference` and `novelty` enums;
- normalization of hyphen/underscore and repeated whitespace;
- stable sorting/deduplication across recognized dimensions;
- negative vocal terms (`without vocals`, `no vocals`, `less vocals`) where distinct parser branches need protection;
- unknown text remaining unstructured.

### M4 — intent-aware retrieval

Prioritize scoring/mapping branches:

- no structured constraints producing zero intent score;
- missing candidate energy producing the documented partial score;
- `any` vocal preference and `any` novelty leaving owned signals unchanged;
- negative vocal matching behavior;
- preservation of non-M4 `CandidateSignals`;
- `enrich_many` and `rank` boundary delegation where not already protected;
- candidate validation and deterministic ordering where currently uncovered.

### M6 — catalog pipeline

Prioritize SQLite-adapter boundary behavior:

- positive/invalid `limit` handling, including `bool`;
- empty `candidates_by_ids` behavior;
- duplicate/blank requested IDs;
- active-only filtering on both full-catalog and ID-selected paths;
- requested-ID order preservation despite SQL ordering;
- malformed JSON vector fields remaining safely unknown;
- bounded energy mapping and unavailable semantic evidence remaining neutral;
- adapter purity/no catalog mutation.

### M10 — contextual novelty and end-to-end composition

Prioritize context/time and composition branches:

- context normalization and empty-context behavior;
- timezone-aware reference-time validation;
- event context isolation and uncontexted-event exclusion;
- no-exposure novelty fallback;
- repeated/older exposure decay behavior where an explicit contract branch is unprotected;
- preservation of non-novelty signals;
- seed dependency failure/success boundary;
- seed exclusion from candidates;
- deterministic composition with empty candidate sets and supplied dependencies.

### M11 — catalog-backed service and CLI/application boundary

Prioritize application-level validation and delegation:

- invalid retrieval mode;
- retrieval-limit validation including `bool`;
- catalog-limit prohibition for non-catalog retrieval;
- semantic/hybrid mode dependency requirements;
- indexed retrieval requirements for model/index paths;
- event-limit forwarding/bounding;
- explicit `seed_track_id` override precedence;
- non-seeded path not constructing learned dependencies;
- CLI parsing/forwarding/error paths for the documented M11 command where still uncovered;
- service non-mutation and deterministic reference-time behavior.

## Non-goals

M17.6 does not add:

- new recommendation behavior;
- new parser vocabulary;
- new sequence modes;
- new ML models;
- new database schema;
- network access;
- cloud inference;
- UI/API work;
- generic repo-wide coverage cleanup;
- tests for branches already directly protected by existing suites.

## Production-change rule

Production changes are out of scope unless a new M17.6 regression test demonstrates an actual contract defect. Any such defect must be documented explicitly and fixed only with the narrowest change plus regression coverage.

## Validation gate

The final report must include:

- exact branch/head SHA;
- fail-first mutation results for each newly protected behavior where practical;
- focused test count;
- full pytest result;
- Ruff result;
- `git diff --check`;
- working-tree status;
- whether any production file changed.

The report must separate newly discovered defects from pre-existing repository validation debt.
