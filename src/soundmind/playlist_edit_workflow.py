"""Deterministic orchestration of parsed playlist edit commands."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from soundmind.playlist_edit_parser import PlaylistEditCommand
from soundmind.playlist_edit_resolution import resolve_playlist_edit_references
from soundmind.playlist_editing import (
    MoveTrack,
    MoveTrackAfter,
    MoveTrackBefore,
    PlaylistEdit,
    RemoveTrack,
    SwapTracks,
    TrimPlaylist,
    apply_playlist_edits,
)
from soundmind.playlist_filter import (
    PlaylistMetadataFilter,
    playlist_filter_to_edits,
)
from soundmind.sequence import SequenceItem


@dataclass(frozen=True)
class PlaylistEditPlanStep:
    """One parsed command, its resolved structural edits, and resulting playlist."""

    command: PlaylistEditCommand
    resolved_edits: tuple[PlaylistEdit, ...]
    playlist: tuple[SequenceItem, ...]


def _resolve_command(
    session: Session,
    playlist: tuple[SequenceItem, ...],
    command: PlaylistEditCommand,
) -> tuple[PlaylistEdit, ...]:
    if isinstance(command, PlaylistMetadataFilter):
        return playlist_filter_to_edits(session, playlist, command)
    return resolve_playlist_edit_references(session, playlist, [command])


def plan_playlist_edit_commands(
    session: Session,
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    commands: Sequence[PlaylistEditCommand],
) -> tuple[PlaylistEditPlanStep, ...]:
    """Resolve and apply commands in order while recording each resulting state."""
    result = tuple(items)
    steps: list[PlaylistEditPlanStep] = []
    for command in commands:
        edits = _resolve_command(session, result, command)
        result = apply_playlist_edits(result, edits)
        steps.append(
            PlaylistEditPlanStep(
                command=command,
                resolved_edits=tuple(edits),
                playlist=result,
            )
        )
    return tuple(steps)


def apply_playlist_edit_commands(
    session: Session,
    items: tuple[SequenceItem, ...] | list[SequenceItem],
    commands: Sequence[PlaylistEditCommand],
) -> tuple[SequenceItem, ...]:
    """Apply parsed edits and filters against the current playlist state."""
    steps = plan_playlist_edit_commands(session, items, commands)
    if not steps:
        return tuple(items)
    return steps[-1].playlist


def describe_playlist_edit(edit: PlaylistEdit) -> str:
    """Return a stable human-readable description of one structural edit."""
    if isinstance(edit, RemoveTrack):
        return f"remove {edit.track_id}"
    if isinstance(edit, MoveTrack):
        return f"move {edit.track_id} to position {edit.position + 1}"
    if isinstance(edit, MoveTrackBefore):
        return f"move {edit.track_id} before {edit.target_track_id}"
    if isinstance(edit, MoveTrackAfter):
        return f"move {edit.track_id} after {edit.target_track_id}"
    if isinstance(edit, SwapTracks):
        return f"swap {edit.first_track_id} with {edit.second_track_id}"
    if isinstance(edit, TrimPlaylist):
        return f"trim to {edit.limit}"
    raise TypeError(f"unsupported playlist edit: {type(edit).__name__}")


def describe_playlist_command(command: PlaylistEditCommand) -> str:
    """Return a stable human-readable description of one parsed command."""
    if isinstance(command, PlaylistMetadataFilter):
        action = (
            "remove all tracks"
            if command.action.value == "remove"
            else "keep only tracks"
        )
        field = command.field.value
        if field == "artist":
            return f"{action} by {command.value}"
        if field == "album":
            return f"{action} from album {command.value}"
        if field == "genre":
            return f"{action} in genre {command.value}"
        raise TypeError(f"unsupported playlist filter field: {field!r}")
    return describe_playlist_edit(command)
