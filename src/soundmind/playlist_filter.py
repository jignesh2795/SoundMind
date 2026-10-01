"""Deterministic catalog-backed metadata filters for generated playlists."""

from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from soundmind.playlist_editing import RemoveTrack, PlaylistEdit
from soundmind.sequence import SequenceItem
from soundmind.storage.models import TrackRow


class PlaylistFilterAction(str, Enum):
    REMOVE = "remove"
    KEEP_ONLY = "keep_only"


class PlaylistFilterField(str, Enum):
    ARTIST = "artist"
    ALBUM = "album"
    GENRE = "genre"


@dataclass(frozen=True)
class PlaylistMetadataFilter:
    action: PlaylistFilterAction
    field: PlaylistFilterField
    value: str


def _normalized(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _genre_values(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(
        sorted({_normalized(part) for part in value.split(",") if _normalized(part)})
    )


def _matches(row: TrackRow, *, field: PlaylistFilterField, value: str) -> bool:
    normalized = _normalized(value)
    if field is PlaylistFilterField.ARTIST:
        return bool(row.artist) and _normalized(row.artist) == normalized
    if field is PlaylistFilterField.ALBUM:
        return bool(row.album) and _normalized(row.album) == normalized
    if field is PlaylistFilterField.GENRE:
        return normalized in _genre_values(row.genre)
    raise ValueError(f"unsupported playlist filter field: {field!r}")


def playlist_filter_to_edits(
    session: Session,
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    filter_edit: PlaylistMetadataFilter,
) -> tuple[PlaylistEdit, ...]:
    """Resolve a metadata filter into deterministic RemoveTrack edits."""
    playlist = tuple(items)
    if not isinstance(filter_edit, PlaylistMetadataFilter):
        raise TypeError(
            f"unsupported playlist filter: {type(filter_edit).__name__}"
        )
    value = _normalized(filter_edit.value)
    if not value:
        raise ValueError("filter value must be non-empty")

    track_ids = tuple(item.track_id for item in playlist)
    if not track_ids:
        return ()

    rows = session.scalars(
        select(TrackRow).where(
            TrackRow.status == "active",
            TrackRow.track_id.in_(track_ids),
        )
    )
    by_id = {row.track_id: row for row in rows}

    matches = {
        track_id
        for track_id in track_ids
        if track_id in by_id
        and _matches(by_id[track_id], field=filter_edit.field, value=value)
    }

    if filter_edit.action is PlaylistFilterAction.REMOVE:
        selected = matches
    elif filter_edit.action is PlaylistFilterAction.KEEP_ONLY:
        selected = set(track_ids) - matches
    else:
        raise ValueError(f"unsupported playlist filter action: {filter_edit.action!r}")

    return tuple(RemoveTrack(track_id) for track_id in track_ids if track_id in selected)
