# M16.2 — Deterministic M3U8 Playlist Import

## Purpose

M16.2 adds a deterministic local import path for simple M3U8 playlists previously exported by M16.1 or compatible local producers.

## Command

`playlist m3u8-import INPUT --name NAME [--replace-existing]` reads a local UTF-8 M3U8 document and persists it as a named SoundMind playlist.

M3U8 does not provide a reliable SoundMind playlist name, so the destination name is required explicitly.

## Resolution

Each source entry must be a local `file://` URI.

The importer resolves each URI by exact match against the active catalog's `TrackRow.source_uri`. Playlist order is preserved.

Imported items receive `sequence_score=0.0` and `base_score=0.0` because M3U8 does not carry SoundMind's ranking/sequencing evidence.

## Validation

The parser requires:

- a leading `#EXTM3U` header;
- each source URI to be preceded by one `#EXTINF` record;
- numeric `#EXTINF` duration values;
- local `file://` source URIs;
- source URIs that resolve to active catalog tracks;
- no duplicate source URIs;
- no dangling `#EXTINF` entries.

Other comment lines are ignored.

## Persistence

An existing destination playlist is rejected unless `--replace-existing` is supplied.

Successful persistence uses `PlaylistRepository.save` followed by one CLI transaction commit.

## Boundaries

M16.2 does not:

- recreate M2 sequence scores;
- recreate M1 ranking scores;
- alter catalog metadata;
- re-rank or re-sequence imported tracks;
- perform network requests or playback;
- require an LLM or cloud model.

M3U8 remains a lossy playback-oriented interchange format. M15 JSON remains the lossless SoundMind playlist interchange format.

## Output

```text
soundmind playlist m3u8-import exports/focus.m3u8 --name "Focus Music"

Imported M3U8 playlist: Focus Music <- exports/focus.m3u8
```

## Validation

M16.2 requires the normal project gate before closeout:

```text
Ruff: All checks passed!
pytest: <validated count> passed, 0 failed
git diff --check: clean
working tree: clean
```

Validated gate at implementation head `310261fe9967c6aeb2be2f59fb31872de798464c`:

```text
Ruff: All checks passed!
pytest: 366 passed, 0 failed
git diff --check: clean
working tree: clean
```

The implementation was merged to `main` as merge commit `2c5f426cf24d9497cb57a19fb43f271839f0720d`.
