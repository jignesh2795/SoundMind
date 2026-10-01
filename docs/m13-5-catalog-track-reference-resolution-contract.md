# M13.5 — Catalog Track Reference Resolution

## Purpose

M13.5 lets playlist edit commands refer to tracks using exact catalog metadata instead of requiring internal track IDs.

The resolver is an input adapter. The M13.1 structural editor remains responsible for applying edits and enforcing playlist membership.

## Resolution rules

For each track reference used by a playlist edit:

1. an exact existing playlist track ID is used unchanged;
2. otherwise an exact case-insensitive title match within the current playlist is accepted when unique;
3. otherwise an exact case-insensitive filename match within the current playlist is accepted when unique;
4. an unmatched reference is left unchanged so M13.1 can reject it as a missing track;
5. multiple exact metadata matches are rejected as ambiguous.

Whitespace around a metadata reference is normalized, and repeated internal whitespace is treated equivalently.

Matching is exact after normalization. No fuzzy token matching, semantic similarity, partial matching, or LLM interpretation is introduced.

## Supported edit operations

Resolution applies to the referenced tracks in:

- RemoveTrack;
- MoveTrack;
- MoveTrackBefore;
- MoveTrackAfter;
- SwapTracks.

TrimPlaylist has no track reference and is unchanged.

## Examples

A playlist containing track ID track-a with title Hero Theme can accept:

    remove track-a
    remove Hero Theme

A filename reference can also be used:

    move hero-theme.mp3 to 1

Ambiguous metadata is rejected:

    remove Hero Theme

when more than one playlist track has that exact title.

## Boundary

The flow remains:

    recommend
        ↓
    M1 ranking
        ↓
    M2 sequencing
        ↓
    M13.2 command parsing
        ↓
    M13.5 exact track-reference resolution
        ↓
    M13.1 structural editing
        ↓
    edited playlist

Resolution does not search outside the generated playlist and does not add new tracks.

## Determinism

Resolution depends only on the current playlist, active catalog metadata, and the supplied edit references.

It has no network, model, randomness, or clock dependency.

The input playlist and parsed edit objects are not mutated.

## Explicit exclusions

M13.5 does not provide:

- fuzzy or partial track matching;
- semantic track matching;
- artist/genre bulk selection;
- automatic replacement-track discovery;
- adding tracks not already in the generated playlist;
- persistence;
- playback-provider integration;
- re-ranking after editing;
- LLM-based interpretation.
