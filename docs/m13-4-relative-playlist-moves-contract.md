# M13.4 — Relative Playlist Moves

## Purpose

M13.4 extends the deterministic M13.1 playlist editor with relative movement commands.

A caller can move one existing track immediately before or after another existing track without calculating an absolute playlist position.

## Scope

M13.4 adds two structural edit operations:

- move one existing track immediately before another track;
- move one existing track immediately after another track.

The existing absolute-position move remains unchanged.

## Contract

MoveTrackBefore(track_id, target_track_id) moves track_id immediately before target_track_id.

MoveTrackAfter(track_id, target_track_id) moves track_id immediately after target_track_id.

Both track IDs must be present in the current playlist and must be distinct.

The operations are applied sequentially with all existing M13.1 edit semantics. Earlier edits can therefore change which position a later relative move produces.

The M13.2 parser accepts human-facing commands such as:

    move hero-theme before intro-track
    move outro-theme after hero-theme
    move track-a before track-b
    move track-a after track-b

Track IDs are still treated as literal identifiers. The parser does not resolve metadata or infer similar tracks.

## Position semantics

Relative movement is defined against the playlist state immediately before the edit.

The target remains in the playlist and the moved track is inserted adjacent to it:

    move c before b
    [a, b, c, d] → [a, c, b, d]

    move a after c
    [a, b, c, d] → [b, c, a, d]

When the source track originally lies on the other side of the target, the implementation recomputes the target position after removing the source so the final adjacency is deterministic.

## Determinism and immutability

Relative moves have no network, model, randomness, or clock dependency.

The input playlist is never mutated.

For identical playlist state and identical ordered edits, the resulting playlist is identical.

## Boundary

The relative move extension remains inside the existing playlist-editing boundary:

    recommendation
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
    edited playlist

Relative moves do not feed back into ranking or sequencing.

## Explicit exclusions

M13.4 does not provide:

- automatic replacement-track discovery;
- semantic or fuzzy track matching;
- catalog lookup for unresolved track IDs;
- persistence;
- playback-provider integration;
- re-ranking after editing;
- LLM-based interpretation.

Those capabilities require separate contracts.
