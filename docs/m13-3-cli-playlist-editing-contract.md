# M13.3 — CLI Playlist Editing Workflow

## Purpose

M13.3 connects the M13.2 natural-language playlist edit parser and M13.1 structural editor to the existing recommendation CLI.

A recommendation can now be generated normally and then edited in the same command invocation.

## CLI contract

The `recommend` command accepts repeatable `--edit` options.

Examples:

    soundmind recommend "cinematic BGM" \
        --context coding \
        --edit "remove intro-track"

    soundmind recommend "high energy BGM" \
        --context coding \
        --edit "remove track-a" \
        --edit "move track-d to 1"

Each command is parsed by M13.2 and applied by M13.1 in the order supplied.

Human-facing move positions remain one-based.

## Ordering boundary

The workflow is:

    intent / retrieval
        ↓
    M1 ranking
        ↓
    M2 sequencing
        ↓
    generated playlist
        ↓
    M13.2 command parsing
        ↓
    M13.1 structural editing
        ↓
    CLI playlist output

The ranked recommendation output is not rewritten by edits. Only the playlist output is edited.

## Determinism

For the same recommendation result and the same ordered edit commands, the resulting playlist is deterministic.

No model, network, randomness, persistence, or clock dependency is introduced by the editing step.

Existing `recommend` behavior is unchanged when no `--edit` option is supplied.

## Errors

Parser errors are surfaced for unsupported or malformed commands.

After parsing, M13.1 validates playlist state. Referencing a track that is not present in the generated playlist is rejected rather than silently ignored.

## Explicit exclusions

M13.3 does not provide:

- automatic replacement-track discovery;
- semantic or fuzzy track matching;
- persistent saved playlists;
- playback-provider integration;
- re-ranking after an edit;
- LLM-based command interpretation.

Those capabilities can be introduced as separate contracts.
