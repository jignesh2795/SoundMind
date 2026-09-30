# M12.7 — Deterministic Query Expansion Contract

## Purpose

M12.7 adds an explicit, opt-in query-expansion layer for lexical catalog retrieval.

The goal is to improve recall when a user uses common music-domain terms that appear in catalogs under an equivalent phrase or abbreviation.

The expansion layer is deterministic and local. It does not invoke an LLM, network service, model, or external thesaurus.

## Scope

M12.7 covers:

- lexical catalog search;
- the lexical side of live hybrid retrieval;
- the lexical side of persisted hybrid retrieval;
- recommendation candidate generation when the selected mode contains lexical retrieval;
- CLI opt-in controls.

M12.7 does not alter:

- semantic embedding behavior;
- persisted semantic index contents;
- M12 hybrid fusion mathematics;
- M1 ranking;
- M2 sequencing;
- SQLite schema;
- default retrieval behavior.

## Expansion rules

The initial vocabulary is deliberately small and music-domain specific.

Supported examples include:

```
bgm                  ↔ background music
bgm                  ↔ background score
ost                  ↔ soundtrack
ost                  ↔ original soundtrack
theme song           ↔ theme music
film score           ↔ movie score
```

The original query is always retained.

Expansion is phrase-aware and case-insensitive. Unknown terms are left unchanged.

## Retrieval semantics

Expansion is applied as multiple lexical query variants.

For each catalog track, the engine keeps the best deterministic score across the original and expanded variants. It does not concatenate aliases into one longer query, avoiding artificial dilution of the original query-token coverage.

Stable track-ID ordering remains the final tie breaker.

For hybrid retrieval:

```
expanded lexical retrieval
        +
original semantic retrieval
        ↓
existing M12.4 fusion
```

Semantic embeddings therefore continue to represent the user's original query.

## Default behavior

Expansion is **off by default**.

Existing commands therefore retain their previous behavior.

Opt-in examples:

```bash
soundmind search "hero bgm" --expand-query
soundmind search "hero bgm" --hybrid --expand-query
soundmind recommend "hero bgm" --context coding --retrieval hybrid --expand-query
```

## Determinism

For a fixed query, catalog state, expansion vocabulary, retrieval mode, and limit, expansion produces the same query variants and lexical results.

No randomness, network access, model inference, or mutable external vocabulary is involved.

## Boundaries

M12.7 is retrieval recall infrastructure.

```
user query
    ↓
optional deterministic expansion
    ↓
M12 lexical / hybrid candidate generation
    ↓
candidate IDs
    ↓
M1 ranking
    ↓
M2 sequencing
```

Expansion does not become a recommendation score and does not bypass the existing ranking boundary.

## Validation

Validation is performed through the project's OpenCode local gate before merge.

The implementation includes focused unit coverage for:

- phrase and abbreviation expansion;
- case-insensitive matching;
- deduplication;
- no-op behavior for unknown terms;
- lexical engine integration with opt-in expansion.
