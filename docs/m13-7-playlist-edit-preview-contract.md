# M13.7 — Deterministic Playlist Edit Preview

## Purpose

M13.7 adds an explicit preview surface for playlist edit commands.

The preview resolves and applies the same deterministic commands used by the normal editing workflow, but exposes the command-by-command plan and resulting playlist separately from normal playlist output.

## CLI contract

The recommendation CLI accepts:

    soundmind recommend "cinematic BGM" \
        --context coding \
        --edit "remove Hero Theme" \
        --edit "move hero-theme.mp3 after Chorus Theme" \
        --preview-edits

Preview mode requires at least one --edit command.

The ranked recommendation section remains available and is not changed by preview mode.

Instead of the normal Playlist: section, preview mode emits:

    Edit preview:
    1. command: remove track-a
       -> remove track-a
    ...
    Playlist preview:
    1. track-id
    ...

The command description is normalized and the structural edit description shows resolved internal track IDs where catalog resolution was used.

## Planning semantics

Commands are processed in caller-supplied order.

Each command is resolved against the playlist state produced by all preceding commands.

The preview records, for each step:

- the parsed command;
- the resolved structural edit operations;
- the playlist state after those operations.

No external or persistent state is changed by preview mode.

## Boundary

The flow remains:

    recommendation
        ↓
    M1 ranking
        ↓
    M2 sequencing
        ↓
    M13.2 command parsing
        ↓
    M13.5 reference resolution / M13.6 filtering
        ↓
    M13.1 structural editing
        ↓
    M13.7 deterministic preview presentation

Preview is a presentation layer over the existing editing workflow. It does not introduce a second edit engine.

## Determinism

For identical recommendation output and identical edit commands, the preview plan and resulting playlist are identical.

There is no network, model, randomness, or clock dependency in preview planning.

## Explicit exclusions

M13.7 does not provide:

- automatic replacement-track discovery;
- fuzzy or semantic matching;
- persistent playlist storage;
- playback integration;
- re-ranking;
- LLM-based command interpretation.
