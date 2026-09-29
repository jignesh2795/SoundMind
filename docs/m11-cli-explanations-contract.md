# M11.4 CLI Recommendation Explanations Contract

## Goal

M11.4 exposes the existing per-signal recommendation explanation through the M11 CLI.

The feature is presentation-only. Ranking, fusion weights, signal computation, and persistence contracts remain unchanged.

## Command

    soundmind recommend "<request>" --context <context> --explain [options]

Without `--explain`, the existing M11.3 CLI output remains unchanged.

With `--explain`, each ranked candidate prints:

- total ranked score (existing output);
- strongest contributing signal;
- each existing signal contribution with raw score, normalized weight, and weighted contribution.

## Flow

    Existing recommendation result
        ↓
    RecommendationExplanation
        ↓
    CLI formatter
        ↓
    human-readable explanation

The CLI does not recompute or reinterpret the explanation.

## Ownership

- `soundmind.cli.main` owns formatting and the `--explain` switch;
- `RankedCandidate.explanation` remains the source of truth;
- `RecommendationExplanation` and `SignalContribution` remain owned by the recommendation layer;
- all M3/M4/M8/M9/M10/M1/M2 contracts remain unchanged.

## Determinism

Given the same recommendation result, `--explain` produces deterministic text because it formats stored explanation fields in their existing order.

## Non-goals

M11.4 does not add:

- new ranking logic;
- new explanation calculations;
- new database tables;
- model downloads;
- LLM or cloud inference;
- GUI work.

## Acceptance

M11.4 is complete when:

1. the recommendation command accepts `--explain`;
2. default output remains unchanged without the flag;
3. explanation output includes the strongest signal and existing per-signal contributions;
4. no ranking or persistence code changes are required;
5. unit tests cover explanation formatting.
