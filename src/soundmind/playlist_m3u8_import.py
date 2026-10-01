"""Deterministic parsing of local M3U8 playlist exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from soundmind.sequence import SequenceItem


@dataclass(frozen=True)
class ParsedM3U8Playlist:
    """Ordered playlist items resolved from local catalog source URIs."""

    items: tuple[SequenceItem, ...]


def parse_m3u8(
    text: str,
    tracks_by_source_uri: dict[str, str],
) -> ParsedM3U8Playlist:
    """Parse a simple UTF-8 M3U8 document using exact local source-URI matching."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("M3U8 playlist must start with #EXTM3U")

    items: list[SequenceItem] = []
    pending_extinf = False
    seen: set[str] = set()
    seen_track_ids: set[str] = set()

    for line in lines[1:]:
        if line.startswith("#"):
            if line.startswith("#EXTINF:"):
                if pending_extinf:
                    raise ValueError("M3U8 contains consecutive #EXTINF entries")
                if "," not in line:
                    raise ValueError("M3U8 #EXTINF entry must contain a label")
                duration_text, _label = line[len("#EXTINF:") :].split(",", 1)
                try:
                    float(duration_text)
                except ValueError as exc:
                    raise ValueError("M3U8 #EXTINF duration must be numeric") from exc
                pending_extinf = True
            continue

        if not line.startswith("file://"):
            raise ValueError(f"M3U8 source is not a local file URI: {line!r}")
        if pending_extinf is False:
            raise ValueError(f"M3U8 source is missing a preceding #EXTINF: {line!r}")
        if line in seen:
            raise ValueError(f"duplicate M3U8 source URI: {line!r}")

        track_id = tracks_by_source_uri.get(line)
        if track_id is None:
            raise ValueError(f"M3U8 source not found in catalog: {line!r}")
        if track_id in seen_track_ids:
            raise ValueError(f"duplicate catalog track ID: {track_id!r}")
        seen.add(line)
        seen_track_ids.add(track_id)
        items.append(
            SequenceItem(
                track_id=track_id,
                sequence_score=0.0,
                base_score=0.0,
            )
        )
        pending_extinf = False

    if pending_extinf:
        raise ValueError("M3U8 #EXTINF entry is missing a source URI")

    return ParsedM3U8Playlist(items=tuple(items))


def load_m3u8(
    path: Path,
    tracks_by_source_uri: dict[str, str],
) -> ParsedM3U8Playlist:
    """Load a local UTF-8 M3U8 file and resolve its source URIs."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"could not read M3U8 playlist: {path}") from exc
    return parse_m3u8(text, tracks_by_source_uri)
