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
class PlaylistEditChange:
    """One position or membership change between two playlist states."""

    track_id: str
    from_position: int | None
    to_position: int | None


@dataclass(frozen=True)
class PlaylistEditPlanStep:
    """One parsed command, its resolved edits, diff, and resulting playlist."""

    command: PlaylistEditCommand
    resolved_edits: tuple[PlaylistEdit, ...]
    changes: tuple[PlaylistEditChange, ...]
    playlist: tuple[SequenceItem, ...]


def _resolve_command(
    session: Session,
    playlist: tuple[SequenceItem, ...],
    command: PlaylistEditCommand,
) -> tuple[PlaylistEdit, ...]:
    if isinstance(command, PlaylistMetadataFilter):
        return playlist_filter_to_edits(session, playlist, command)
    return resolve_playlist_edit_references(session, playlist, [command])


def diff_playlist_states(
    before: tuple[SequenceItem, ...] | list[SequenceItem],
    after: tuple[SequenceItem, ...] | list[SequenceItem],
) -> tuple[PlaylistEditChange, ...]:
    """Return deterministic membership and position changes between states."""
    before_items = tuple(before)
    after_items = tuple(after)
    before_ids = tuple(item.track_id for item in before_items)
    after_ids = tuple(item.track_id for item in after_items)

    if len(before_ids) != len(set(before_ids)):
        raise ValueError("duplicate track_id in before playlist")
    if len(after_ids) != len(set(after_ids)):
        raise ValueError("duplicate track_id in after playlist")

    before_positions = {track_id: index for index, track_id in enumerate(before_ids)}
    after_positions = {track_id: index for index, track_id in enumerate(after_ids)}
    changes: list[PlaylistEditChange] = []

    for track_id in before_ids:
        before_position = before_positions[track_id]
        after_position = after_positions.get(track_id)
        if after_position != before_position:
            changes.append(
                PlaylistEditChange(
                    track_id=track_id,
                    from_position=before_position,
                    to_position=after_position,
                )
            )

    for track_id in after_ids:
        if track_id not in before_positions:
            changes.append(
                PlaylistEditChange(
                    track_id=track_id,
                    from_position=None,
                    to_position=after_positions[track_id],
                )
            )

    return tuple(changes)


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
        before = result
        result = apply_playlist_edits(result, edits)
        steps.append(
            PlaylistEditPlanStep(
                command=command,
                resolved_edits=tuple(edits),
                changes=diff_playlist_states(before, result),
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


def describe_playlist_edit_change(change: PlaylistEditChange) -> str:
    """Return a stable human-readable description of one playlist-state change."""
    if change.from_position is None:
        if change.to_position is None:
            raise ValueError("playlist change must have at least one position")
        return f"add {change.track_id} at position {change.to_position + 1}"
    if change.to_position is None:
        return f"remove {change.track_id} from position {change.from_position + 1}"
    return (
        f"move {change.track_id} from position {change.from_position + 1} "
        f"to position {change.to_position + 1}"
    )


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
