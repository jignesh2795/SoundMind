"""Deterministic repair planning for persisted playlists."""

from __future__ import annotations

from dataclasses import dataclass

from soundmind.playlist_audit import audit_playlist
from soundmind.sequence import SequenceItem


@dataclass(frozen=True)
class PlaylistRepairEntry:
    """Repair action for one persisted playlist track reference."""

    track_id: str
    status: str
    action: str


@dataclass(frozen=True)
class PlaylistRepairPlan:
    """Ordered, read-only playlist repair plan."""

    entries: tuple[PlaylistRepairEntry, ...]

    @property
    def keep_count(self) -> int:
        return sum(entry.action == "keep" for entry in self.entries)

    @property
    def remove_count(self) -> int:
        return sum(entry.action == "remove" for entry in self.entries)


def plan_playlist_repair(
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    catalog_status_by_id: dict[str, str],
) -> PlaylistRepairPlan:
    """Plan removal of every non-active playlist reference without mutation."""
    audit = audit_playlist(items, catalog_status_by_id)
    entries = tuple(
        PlaylistRepairEntry(
            track_id=entry.track_id,
            status=entry.status,
            action="keep" if entry.status == "active" else "remove",
        )
        for entry in audit.entries
    )
    return PlaylistRepairPlan(entries=entries)
