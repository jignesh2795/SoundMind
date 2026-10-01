"""Deterministic integrity diagnostics for persisted playlists."""

from __future__ import annotations

from dataclasses import dataclass

from soundmind.sequence import SequenceItem


@dataclass(frozen=True)
class PlaylistAuditEntry:
    """Audit status for one persisted playlist track reference."""

    track_id: str
    status: str


@dataclass(frozen=True)
class PlaylistAudit:
    """Ordered playlist integrity report."""

    entries: tuple[PlaylistAuditEntry, ...]

    @property
    def active_count(self) -> int:
        return sum(entry.status == "active" for entry in self.entries)

    @property
    def inactive_count(self) -> int:
        return sum(entry.status == "inactive" for entry in self.entries)

    @property
    def missing_count(self) -> int:
        return sum(entry.status == "missing" for entry in self.entries)


def audit_playlist(
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    catalog_status_by_id: dict[str, str],
) -> PlaylistAudit:
    """Classify each persisted track reference without mutating state."""
    entries = tuple(
        PlaylistAuditEntry(
            track_id=item.track_id,
            status=(
                "active"
                if catalog_status_by_id.get(item.track_id) == "active"
                else (
                    "inactive"
                    if item.track_id in catalog_status_by_id
                    else "missing"
                )
            ),
        )
        for item in items
    )
    return PlaylistAudit(entries=entries)
