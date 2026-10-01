"""Local persistence for named playlist snapshots."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from soundmind.sequence import SequenceItem
from soundmind.storage.models import PlaylistItemRow, PlaylistRow


@dataclass(frozen=True)
class SavedPlaylist:
    """Persisted named playlist with its ordered sequence items."""

    name: str
    items: tuple[SequenceItem, ...]
    created_at: datetime
    updated_at: datetime


def _normalize_name(name: str) -> tuple[str, str]:
    if name is None or not name.strip():
        raise ValueError("playlist name must be non-empty")
    display_name = " ".join(name.split())
    return display_name, display_name.casefold()


def _validate_items(items: tuple[SequenceItem, ...]) -> None:
    seen: set[str] = set()
    for item in items:
        if not item.track_id:
            raise ValueError("track_id must be non-empty")
        if item.track_id in seen:
            raise ValueError(f"duplicate track_id: {item.track_id!r}")
        seen.add(item.track_id)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_saved_playlist(
    playlist: PlaylistRow,
    rows: list[PlaylistItemRow],
) -> SavedPlaylist:
    items = tuple(
        SequenceItem(
            track_id=row.track_id,
            sequence_score=row.sequence_score,
            base_score=row.base_score,
        )
        for row in rows
    )
    return SavedPlaylist(
        name=playlist.name,
        items=items,
        created_at=_as_utc(playlist.created_at),
        updated_at=_as_utc(playlist.updated_at),
    )


class PlaylistRepository:
    """Persist and retrieve named playlist snapshots using the caller session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        name: str,
        items: tuple[SequenceItem, ...] | list[SequenceItem],
        *,
        now: datetime | None = None,
    ) -> SavedPlaylist:
        """Create or replace a named playlist snapshot without committing."""
        display_name, name_key = _normalize_name(name)
        normalized_items = tuple(items)
        _validate_items(normalized_items)
        timestamp = now or datetime.now(UTC)

        playlist = self._session.scalar(
            select(PlaylistRow).where(PlaylistRow.name_key == name_key)
        )
        if playlist is None:
            playlist = PlaylistRow(
                name=display_name,
                name_key=name_key,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self._session.add(playlist)
            self._session.flush()
        else:
            playlist.name = display_name
            playlist.updated_at = timestamp
            self._session.execute(
                delete(PlaylistItemRow).where(
                    PlaylistItemRow.playlist_id == playlist.playlist_id
                )
            )

        self._session.add_all(
            [
                PlaylistItemRow(
                    playlist_id=playlist.playlist_id,
                    position=position,
                    track_id=item.track_id,
                    sequence_score=item.sequence_score,
                    base_score=item.base_score,
                )
                for position, item in enumerate(normalized_items)
            ]
        )
        self._session.flush()
        saved = self.get(display_name)
        if saved is None:
            raise RuntimeError("saved playlist could not be reloaded")
        return saved

    def get(self, name: str) -> SavedPlaylist | None:
        """Return one named playlist or None when it does not exist."""
        _, name_key = _normalize_name(name)
        playlist = self._session.scalar(
            select(PlaylistRow).where(PlaylistRow.name_key == name_key)
        )
        if playlist is None:
            return None
        rows = list(
            self._session.scalars(
                select(PlaylistItemRow)
                .where(PlaylistItemRow.playlist_id == playlist.playlist_id)
                .order_by(PlaylistItemRow.position)
            ).all()
        )
        return _to_saved_playlist(playlist, rows)

    def list(self) -> tuple[SavedPlaylist, ...]:
        """Return all named playlists in deterministic name order."""
        playlists = self._session.scalars(
            select(PlaylistRow).order_by(PlaylistRow.name_key)
        ).all()
        result = []
        for playlist in playlists:
            rows = list(
                self._session.scalars(
                    select(PlaylistItemRow)
                    .where(PlaylistItemRow.playlist_id == playlist.playlist_id)
                    .order_by(PlaylistItemRow.position)
                ).all()
            )
            result.append(_to_saved_playlist(playlist, rows))
        return tuple(result)
