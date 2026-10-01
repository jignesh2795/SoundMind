"""Deterministic natural-language parsing for playlist structural edits."""

import re
from collections.abc import Sequence

from soundmind.playlist_editing import (
    MoveTrack,
    MoveTrackAfter,
    MoveTrackBefore,
    PlaylistEdit,
    RemoveTrack,
    SwapTracks,
    TrimPlaylist,
)
from soundmind.playlist_filter import (
    PlaylistFilterAction,
    PlaylistFilterField,
    PlaylistMetadataFilter,
)

_REMOVE_RE = re.compile(
    r"^(?:remove|delete|drop|skip)(?:\s+track)?\s+(?P<track>.+)$",
    re.IGNORECASE,
)
_MOVE_RELATIVE_RE = re.compile(
    r"^move(?:\s+track)?\s+(?P<track>.+?)\s+(?P<relation>before|after)\s+"
    r"(?:track\s+)?(?P<target>.+)$",
    re.IGNORECASE,
)
_FILTER_RE = re.compile(
    r"^(?P<action>remove\s+all|keep\s+only)\s+"
    r"(?:tracks?\s+)?"
    r"(?:(?:by\s+(?P<artist>.+))|"
    r"(?:from\s+album\s+(?P<album>.+))|"
    r"(?:in\s+genre\s+(?P<genre>.+)))$",
    re.IGNORECASE,
)
_MOVE_RE = re.compile(
    r"^move(?:\s+track)?\s+(?P<track>.+?)\s+(?:to|into|position)\s+"
    r"(?:position\s+)?(?P<position>\d+)$",
    re.IGNORECASE,
)
_SWAP_RE = re.compile(
    r"^(?:swap|switch)(?:\s+tracks?)?\s+(?P<first>.+?)\s+"
    r"(?:with|and)\s+(?P<second>.+)$",
    re.IGNORECASE,
)
_TRIM_RE = re.compile(
    r"^(?:trim|shorten|limit)\s+(?:playlist\s+)?(?:to|at)\s+(?P<limit>\d+)$",
    re.IGNORECASE,
)
_KEEP_RE = re.compile(
    r"^(?:keep|retain)\s+(?:the\s+)?(?:first\s+)?(?P<limit>\d+)"
    r"(?:\s+(?:tracks?|items?))?$",
    re.IGNORECASE,
)


def _normalize_command(text: str) -> str:
    if text is None or not text.strip():
        raise ValueError("text must be non-empty")
    return re.sub(r"\s+", " ", text).strip()


def _track_id(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in "\"'":
        normalized = normalized[1:-1].strip()
    if not normalized:
        raise ValueError("track_id must be non-empty")
    return normalized


def _positive_integer(value: str, *, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def parse_playlist_edit(text: str) -> PlaylistEdit | PlaylistMetadataFilter:
    """Parse one explicit playlist-edit command into an M13.1 edit."""
    command = _normalize_command(text)

    if match := _FILTER_RE.fullmatch(command):
        value_field = (
            (PlaylistFilterField.ARTIST, match.group("artist"))
            if match.group("artist") is not None
            else (PlaylistFilterField.ALBUM, match.group("album"))
            if match.group("album") is not None
            else (PlaylistFilterField.GENRE, match.group("genre"))
        )
        field, value = value_field
        action = (
            PlaylistFilterAction.KEEP_ONLY
            if match.group("action").casefold().startswith("keep")
            else PlaylistFilterAction.REMOVE
        )
        return PlaylistMetadataFilter(action=action, field=field, value=_track_id(value))

    if match := _REMOVE_RE.fullmatch(command):
        return RemoveTrack(_track_id(match.group("track")))

    if match := _MOVE_RELATIVE_RE.fullmatch(command):
        track_id = _track_id(match.group("track"))
        target_track_id = _track_id(match.group("target"))
        if track_id == target_track_id:
            raise ValueError("relative move requires two distinct track IDs")
        if match.group("relation").casefold() == "before":
            return MoveTrackBefore(track_id, target_track_id)
        return MoveTrackAfter(track_id, target_track_id)

    if match := _MOVE_RE.fullmatch(command):
        human_position = _positive_integer(match.group("position"), name="position")
        return MoveTrack(
            _track_id(match.group("track")),
            human_position - 1,
        )

    if match := _SWAP_RE.fullmatch(command):
        first = _track_id(match.group("first"))
        second = _track_id(match.group("second"))
        if first == second:
            raise ValueError("swap requires two distinct track IDs")
        return SwapTracks(first, second)

    if match := _TRIM_RE.fullmatch(command):
        return TrimPlaylist(_positive_integer(match.group("limit"), name="limit"))

    if match := _KEEP_RE.fullmatch(command):
        return TrimPlaylist(_positive_integer(match.group("limit"), name="limit"))

    raise ValueError(f"unsupported playlist edit command: {text!r}")


def parse_playlist_edits(
    commands: Sequence[str],
) -> tuple[PlaylistEdit | PlaylistMetadataFilter, ...]:
    """Parse multiple explicit commands in caller-supplied order."""
    return tuple(parse_playlist_edit(command) for command in commands)
