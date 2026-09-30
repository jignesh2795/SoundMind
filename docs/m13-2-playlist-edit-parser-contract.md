# M13.2 — Deterministic Natural-Language Playlist Edit Parser

## Purpose

M13.2 adds a small deterministic parser that converts explicit natural-language playlist edit commands into the M13.1 structural edit objects.

The parser is an input adapter. M13.1 remains responsible for validating the current playlist and applying the edit.

## Supported commands

The parser supports one or more commands in caller-supplied order.

### Remove

Examples:

    remove a
    delete track 'hero-01'
    drop track-a
    skip b

Produces RemoveTrack.

### Move

Examples:

    move a to 1
    move track b to position 3
    move 'hero-01' into 2

Human-facing positions are one-based. The parser converts them to the zero-based position required by M13.1.

### Swap

Examples:

    swap a with b
    switch track-a and track-b

Produces SwapTracks.

### Trim / keep

Examples:

    trim to 5
    trim playlist to 3
    limit playlist to 4
    keep first 2 tracks
    retain the first 6 items

Produces TrimPlaylist.

## Contract

parse_playlist_edit(text) returns exactly one M13.1 PlaylistEdit.

parse_playlist_edits(commands) returns a tuple of edits in the same order as the supplied commands.

Whitespace is normalized between command tokens. Track IDs are preserved except for optional matching quote characters at their edges.

Unknown commands, empty input, non-positive positions/limits, and swapping a track with itself are rejected.

The parser does not verify whether a referenced track exists in the current playlist. That resolution remains the responsibility of M13.1.

## Determinism

For identical input, the parser produces identical output.

It has no network, model, randomness, or clock dependency.

Unknown track identifiers are preserved as literal IDs rather than inferred from metadata.

## Boundary

    natural-language edit command
        ↓
    M13.2 deterministic parser
        ↓
    M13.1 PlaylistEdit
        ↓
    M13.1 structural editor
        ↓
    edited playlist

M13.2 does not reorder tracks directly and does not alter recommendation ranking or M2 sequencing.

## Explicit exclusions

M13.2 does not provide:

- LLM-based interpretation;
- semantic or fuzzy track matching;
- intent inference from arbitrary prose;
- automatic replacement-track discovery;
- persistence;
- playback-provider integration.

Those capabilities can be added later behind explicit contracts.
