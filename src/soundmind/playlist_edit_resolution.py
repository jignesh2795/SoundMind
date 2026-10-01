"""Deterministic catalog-backed resolution for playlist edit track references."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from soundmind.playlist_editing import (
    MoveTrack,
    MoveTrackAfter,
    MoveTrackBefore,
    PlaylistEdit,
    RemoveTrack,
    SwapTracks,
    TrimPlaylist,
)
from soundmind.sequence import SequenceItem
from soundmind.storage.models import TrackRow


def _normalized(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _playlist_rows(
    session: Session,
    items: tuple[SequenceItem, ...],
) -> tuple[TrackRow, ...]:
    track_ids = tuple(item.track_id for item in items)
    if not track_ids:
        return ()
    rows = session.scalars(
        select(TrackRow).where(
            TrackRow.status == "active",
            TrackRow.track_id.in_(track_ids),
        )
    )
    return tuple(rows)


def _reference_map(
    session: Session,
    items: tuple[SequenceItem, ...],
) -> dict[str, tuple[str, ...]]:
    mapping: dict[str, set[str]] = {}
    for row in _playlist_rows(session, items):
        for value in (row.title, row.file_name):
            if not value:
                continue
            key = _normalized(value)
            if not key:
                continue
            mapping.setdefault(key, set()).add(row.track_id)
    return {key: tuple(sorted(track_ids)) for key, track_ids in mapping.items()}


def _resolve(
    reference: str,
    *,
    playlist_ids: frozenset[str],
    reference_map: dict[str, tuple[str, ...]],
) -> str:
    if not reference:
        raise ValueError("track reference must be non-empty")
    if reference in playlist_ids:
        return reference

    matches = reference_map.get(_normalized(reference), ())
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = ", ".join(matches)
        raise ValueError(
            f"ambiguous track reference: {reference!r}; matches: {joined}"
        )
    return reference


def resolve_playlist_edit_references(
    session: Session,
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    edits: Iterable[PlaylistEdit],
) -> tuple[PlaylistEdit, ...]:
    """Resolve exact title/filename references to current playlist track IDs."""
    playlist = tuple(items)
    playlist_ids = frozenset(item.track_id for item in playlist)
    references = _reference_map(session, playlist)

    def resolve(reference: str) -> str:
        return _resolve(
            reference,
            playlist_ids=playlist_ids,
            reference_map=references,
        )

    resolved: list[PlaylistEdit] = []
    for edit in edits:
        if isinstance(edit, RemoveTrack):
            resolved.append(RemoveTrack(resolve(edit.track_id)))
            continue
        if isinstance(edit, MoveTrack):
            resolved.append(MoveTrack(resolve(edit.track_id), edit.position))
            continue
        if isinstance(edit, MoveTrackBefore):
            resolved.append(
                MoveTrackBefore(
                    resolve(edit.track_id),
                    resolve(edit.target_track_id),
                )
            )
            continue
        if isinstance(edit, MoveTrackAfter):
            resolved.append(
                MoveTrackAfter(
                    resolve(edit.track_id),
                    resolve(edit.target_track_id),
                )
            )
            continue
        if isinstance(edit, SwapTracks):
            resolved.append(
                SwapTracks(
                    resolve(edit.first_track_id),
                    resolve(edit.second_track_id),
                )
            )
            continue
        if isinstance(edit, TrimPlaylist):
            resolved.append(edit)
            continue
        raise TypeError(f"unsupported playlist edit: {type(edit).__name__}")

    return tuple(resolved)
