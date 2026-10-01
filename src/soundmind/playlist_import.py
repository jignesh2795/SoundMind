"""Validation and parsing for deterministic named-playlist JSON snapshots."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from soundmind.sequence import SequenceItem

SUPPORTED_PLAYLIST_JSON_VERSION = 1


@dataclass(frozen=True)
class ImportedPlaylist:
    """Validated playlist payload ready for persistence."""

    name: str
    items: tuple[SequenceItem, ...]


def _require_mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _require_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _require_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be finite")
    return numeric


def _require_timestamp(value: Any, *, field: str) -> None:
    text = _require_string(value, field=field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    parsed.astimezone(UTC)


def parse_playlist_json(text: str) -> ImportedPlaylist:
    """Validate and parse a version-1 playlist JSON document."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid playlist JSON: {exc.msg}") from exc

    document = _require_mapping(payload, field="playlist")
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("version must be an integer")
    if version != SUPPORTED_PLAYLIST_JSON_VERSION:
        raise ValueError(f"unsupported playlist JSON version: {version!r}")

    name = _require_string(document.get("name"), field="name")
    _require_timestamp(document.get("created_at"), field="created_at")
    _require_timestamp(document.get("updated_at"), field="updated_at")

    raw_items = document.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("items must be an array")

    expected_position = 1
    seen: set[str] = set()
    items: list[SequenceItem] = []
    for raw_item in raw_items:
        item = _require_mapping(raw_item, field="item")
        position = item.get("position")
        if isinstance(position, bool) or not isinstance(position, int):
            raise ValueError("item position must be an integer")
        if position != expected_position:
            raise ValueError(
                f"item positions must be consecutive starting at 1; expected {expected_position}"
            )

        track_id = _require_string(item.get("track_id"), field="track_id")
        if track_id in seen:
            raise ValueError(f"duplicate track_id: {track_id!r}")
        seen.add(track_id)

        sequence_score = _require_number(
            item.get("sequence_score"),
            field="sequence_score",
        )
        base_score = _require_number(
            item.get("base_score"),
            field="base_score",
        )
        items.append(
            SequenceItem(
                track_id=track_id,
                sequence_score=sequence_score,
                base_score=base_score,
            )
        )
        expected_position += 1

    return ImportedPlaylist(name=name, items=tuple(items))


def load_playlist_json(path: Path) -> ImportedPlaylist:
    """Load and validate a playlist JSON snapshot from a local file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"could not read playlist JSON: {path}") from exc
    return parse_playlist_json(text)
