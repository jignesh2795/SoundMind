# M16.1 — Deterministic M3U8 Playlist Export

## Purpose

M16.1 adds a local M3U8 export for persisted named playlists so a SoundMind playlist can be opened by software that understands the M3U8 format.

## Command

`playlist m3u8 NAME OUTPUT` loads a saved playlist and writes a UTF-8 M3U8 document.

The command resolves each persisted track ID against the local catalog. Playlist order is preserved from the saved snapshot.

## Format

The serializer emits:

- `#EXTM3U` header;
- one `#EXTINF` record per track;
- the catalog's local `file://` source URI on the following line;
- duration rounded to the nearest whole second, or `-1` when unavailable;
- title and artist as the display label when present, otherwise the track ID;
- a final newline.

Output is deterministic for the same playlist and catalog state.

## Failure semantics

The export fails without writing an output file when any playlist track is absent from the catalog or its catalog source is not a local `file://` URI.

An empty playlist produces a valid header-only M3U8 document.

## Boundaries

M16.1 does not:

- modify playlist storage;
- modify catalog or listening history;
- change ranking or sequencing;
- mutate playlist membership;
- synchronize with external services;
- require an LLM, cloud model, or network request.

JSON remains the lossless SoundMind playlist interchange format from M15. M3U8 is a derived playback-oriented representation and therefore requires catalog file-source resolution.

## Output

```text
soundmind playlist m3u8 "Focus Music" exports/focus.m3u8

Exported M3U8 playlist: Focus -> exports/focus.m3u8
```

Example:

```text
#EXTM3U
#EXTINF:123,Hero Theme — Composer A
file:///music/hero%20theme.mp3
#EXTINF:-1,Night
file:///music/night.mp3
```

## Validation

M16.1 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

Validated gate at implementation head `0bddff0fa8d20cab1c1d5d8d15e287bf569343f2`:

```text
Ruff: All checks passed!
pytest: 352 passed, 0 failed
git diff --check: clean
working tree: clean
```

The implementation was merged to `main` as merge commit `4dcb57dc45a9c97e34c8e03c872d5a7f629be672`.
