# M13.6 — Deterministic Playlist Metadata Filters

## Purpose

M13.6 adds explicit metadata-based playlist filters that operate on the already generated playlist.

The filter layer is catalog-aware and deterministic. It converts a high-level filter command into the existing M13.1 RemoveTrack edits, keeping structural editing separate from catalog interpretation.

## Supported commands

The M13.2 parser accepts these forms:

    remove all tracks by <artist>
    remove all from album <album>
    remove all tracks in genre <genre>

    keep only tracks by <artist>
    keep only tracks from album <album>
    keep only tracks in genre <genre>

Artist and album matching is exact after case-folding and whitespace normalization.

Genre matching is exact against one of the comma-separated genre values stored on the track.

## Semantics

Filters operate only on the current generated playlist.

For a remove filter, every matching track is removed while the relative order of all remaining tracks is preserved.

For a keep-only filter, every non-matching track is removed while the relative order of matching tracks is preserved.

An empty match set for keep-only therefore produces an empty playlist.

Filter commands are executed sequentially with other M13 edits. A later filter sees the playlist state produced by earlier commands.

## Boundary

The workflow is:

    recommendation
        ↓
    M1 ranking
        ↓
    M2 sequencing
        ↓
    M13.2 command parsing
        ↓
    M13.5 exact track-reference resolution / M13.6 metadata filtering
        ↓
    M13.1 structural editing
        ↓
    edited playlist

Metadata filters do not alter ranked recommendation output, M1 scores, or M2 sequencing.

## Determinism

Filter results depend only on the current playlist, active catalog metadata, and the exact filter command.

No network, model, randomness, fuzzy matching, or clock dependency is introduced.

## Explicit exclusions

M13.6 does not provide:

- fuzzy or semantic metadata matching;
- natural-language inference beyond the explicit parser forms;
- artist/album/genre discovery outside the current playlist;
- adding or replacing tracks;
- persistence;
- playback-provider integration;
- re-ranking after filtering;
- LLM-based interpretation.
