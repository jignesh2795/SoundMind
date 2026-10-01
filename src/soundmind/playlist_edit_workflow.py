"""Deterministic orchestration of parsed playlist edit commands."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from soundmind.playlist_edit_parser import PlaylistEditCommand
from soundmind.playlist_edit_resolution import resolve_playlist_edit_references
from soundmind.playlist_editing import apply_playlist_edits
from soundmind.playlist_filter import (
    PlaylistMetadataFilter,
    playlist_filter_to_edits,
)
from soundmind.sequence import SequenceItem


def apply_playlist_edit_commands(
    session: Session,
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    commands: Sequence[PlaylistEditCommand],
) -> tuple[SequenceItem, ...]:
    """Apply parsed edits and filters against the current playlist state."""
    result = tuple(items)

    for command in commands:
        if isinstance(command, PlaylistMetadataFilter):
            edits = playlist_filter_to_edits(session, result, command)
        else:
            edits = resolve_playlist_edit_references(
                session,
                result,
                [command],
            )
        result = apply_playlist_edits(result, edits)

    return result
