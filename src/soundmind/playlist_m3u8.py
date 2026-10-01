"""Deterministic M3U8 serialization for local playlist exports."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from soundmind.sequence import SequenceItem


@dataclass(frozen=True)
class M3U8Track:
    """Catalog metadata needed to serialize one local playlist entry."""

    source_uri: str
    title: str | None = None
    artist: str | None = None
    duration_seconds: float | None = None


def _duration_seconds(value: float | None) -> int:
    if value is None or not isfinite(value) or value < 0:
        return -1
    return int(round(value))


def _display_name(item: SequenceItem, track: M3U8Track) -> str:
    details = " — ".join(
        value.strip()
        for value in (track.title, track.artist)
        if value and value.strip()
    )
    return details or item.track_id


def saved_playlist_to_m3u8(
    items: Iterable[SequenceItem],
    tracks: dict[str, M3U8Track],
) -> str:
    """Serialize playlist items to a stable UTF-8 M3U8 document."""
    lines = ["#EXTM3U"]
    for item in items:
        track = tracks.get(item.track_id)
        if track is None:
            raise ValueError(f"track not found in catalog: {item.track_id!r}")
        if not track.source_uri.startswith("file://"):
            raise ValueError(
                f"track source is not a local file URI: {item.track_id!r}"
            )
        lines.append(
            f"#EXTINF:{_duration_seconds(track.duration_seconds)},{_display_name(item, track)}"
        )
        lines.append(track.source_uri)
    return "\n".join(lines) + "\n"
