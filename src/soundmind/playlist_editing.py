"""Deterministic structural editing of generated playlists."""

from dataclasses import dataclass

from soundmind.sequence import SequenceItem


@dataclass(frozen=True)
class RemoveTrack:
    """Remove one existing track from the playlist."""

    track_id: str


@dataclass(frozen=True)
class MoveTrack:
    """Move one existing track to an absolute zero-based position."""

    track_id: str
    position: int


@dataclass(frozen=True)
class SwapTracks:
    """Swap the positions of two existing tracks."""

    first_track_id: str
    second_track_id: str


@dataclass(frozen=True)
class TrimPlaylist:
    """Keep only the first limit items."""

    limit: int


type PlaylistEdit = RemoveTrack | MoveTrack | SwapTracks | TrimPlaylist


def _validate_items(items: tuple[SequenceItem, ...]) -> None:
    seen: set[str] = set()
    for item in items:
        if not item.track_id:
            raise ValueError("track_id must be non-empty")
        if item.track_id in seen:
            raise ValueError(f"duplicate track_id: {item.track_id!r}")
        seen.add(item.track_id)


def _index_by_track_id(items: list[SequenceItem]) -> dict[str, int]:
    return {item.track_id: index for index, item in enumerate(items)}


def _require_track(items: list[SequenceItem], track_id: str) -> int:
    if not track_id:
        raise ValueError("track_id must be non-empty")
    index = _index_by_track_id(items).get(track_id)
    if index is None:
        raise ValueError(f"track_id not found: {track_id!r}")
    return index


def apply_playlist_edits(
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    edits: tuple[PlaylistEdit, ...] | list[PlaylistEdit],
) -> tuple[SequenceItem, ...]:
    """Apply explicit structural edits in order without mutating the input."""
    original = tuple(items)
    _validate_items(original)

    result = list(original)
    for edit in edits:
        if isinstance(edit, RemoveTrack):
            index = _require_track(result, edit.track_id)
            result.pop(index)
            continue

        if isinstance(edit, MoveTrack):
            index = _require_track(result, edit.track_id)
            if (
                isinstance(edit.position, bool)
                or not isinstance(edit.position, int)
                or edit.position < 0
                or edit.position >= len(result)
            ):
                raise ValueError("position must be a valid playlist index")
            item = result.pop(index)
            result.insert(edit.position, item)
            continue

        if isinstance(edit, SwapTracks):
            first = _require_track(result, edit.first_track_id)
            second = _require_track(result, edit.second_track_id)
            if edit.first_track_id == edit.second_track_id:
                raise ValueError("swap requires two distinct track IDs")
            result[first], result[second] = result[second], result[first]
            continue

        if isinstance(edit, TrimPlaylist):
            if (
                isinstance(edit.limit, bool)
                or not isinstance(edit.limit, int)
                or edit.limit <= 0
            ):
                raise ValueError("limit must be a positive integer")
            result = result[: edit.limit]
            continue

        raise TypeError(f"unsupported playlist edit: {type(edit).__name__}")

    return tuple(result)
