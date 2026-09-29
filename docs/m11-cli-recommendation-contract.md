# M11.2 CLI Recommendation Contract

## Goal

M11.2 exposes the M11.1 catalog-backed contextual recommendation service through the existing soundmind CLI.

The CLI is an application surface only. It does not add ranking logic, persistence models, schemas, or model downloads.

## Command

    soundmind recommend "<natural-language request>" --context <context> [options]

Options:

- --db: SQLite database path, default data/database/soundmind.db;
- --context: required context label;
- --limit: recommendation/playlist limit, default 10;
- --catalog-limit: optional active-catalog read bound;
- --event-limit: listening-history read bound, default 1000;
- --mode: smooth, contrast, journey, or discovery;
- --now: optional timezone-aware ISO-8601 reference time.

When --now is omitted, the CLI supplies the current UTC time to the service. A timezone is required when --now is provided.

## Flow

    CLI arguments
        ↓
    EndToEndRequest
        ↓
    CatalogContextRecommendationService
        ↓
    SQLite catalog + listening history
        ↓
    M10.3 context-aware flow
        ↓
    ranked candidates + ordered playlist
        ↓
    human-readable CLI output

## Ownership

- soundmind.cli.main owns argument parsing and presentation;
- CatalogContextRecommendationService owns the M11 persistence boundary;
- ContextAwareMusicFlow owns recommendation composition;
- existing M3/M4/M8/M9/M10/M1/M2 layers retain their existing contracts.

## Determinism

The recommendation service always receives an explicit reference time.

Providing --now makes repeated CLI invocations reproducible for the same database state and inputs. Omitting it is a convenience path that intentionally uses the current UTC time.

## Non-goals

M11.2 does not add:

- a new ranking algorithm;
- a new database table or schema;
- automatic learned-model download;
- LLM or cloud inference;
- web/streaming search;
- GUI work.

## Acceptance

M11.2 is complete when:

1. soundmind recommend parses the documented options;
2. the command delegates to M11.1 with an explicit UTC-aware reference time;
3. the selected sequence mode is preserved;
4. the SQLite database path and retrieval bounds are passed through;
5. ranked results and the final playlist are printed deterministically;
6. unit tests cover parsing and service dispatch.
