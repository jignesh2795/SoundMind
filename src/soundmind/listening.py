"""Record and inspect local listening feedback."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.preferences.repository import ListeningEventRepository
from soundmind.storage.models import TrackRow


def record_listening_event(
    session,
    track_id: str,
    event_type: ListeningEventType | str,
    *,
    occurred_at: datetime | None = None,
    context: str | None = None,
    seconds_played: float | None = None,
) -> ListeningEvent:
    """Persist one event for an existing catalog track.

    Track existence, rather than active status, is required so historical
    listening remains recordable after a track is marked inactive.
    """
    if not track_id or not track_id.strip():
        raise KeyError(f"Track not found: {track_id}")
    if session.get(TrackRow, track_id) is None:
        raise KeyError(f"Track not found: {track_id}")

    try:
        normalized_type = ListeningEventType(event_type)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid event type: {event_type!r}") from exc

    if occurred_at is not None:
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        occurred_at = occurred_at.astimezone(UTC)

    if seconds_played is not None and (
        isinstance(seconds_played, bool)
        or not math.isfinite(seconds_played)
        or seconds_played < 0
    ):
        raise ValueError("seconds_played must be finite and non-negative")

    normalized_context = context
    if normalized_context is not None and not normalized_context.strip():
        normalized_context = None

    repository = ListeningEventRepository(session)
    if occurred_at is None:
        row = repository.add_now(
            track_id,
            normalized_type,
            context=normalized_context,
            seconds_played=seconds_played,
        )
        occurred_at = row.occurred_at
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        else:
            occurred_at = occurred_at.astimezone(UTC)
    else:
        repository.add(
            ListeningEvent(
                track_id=track_id,
                event_type=normalized_type,
                occurred_at=occurred_at,
                context=normalized_context,
                seconds_played=seconds_played,
            )
        )

    return ListeningEvent(
        track_id=track_id,
        event_type=normalized_type,
        occurred_at=occurred_at,
        context=normalized_context,
        seconds_played=seconds_played,
    )


def list_listening_events(session, *, limit: int = 20) -> list[ListeningEvent]:
    """Return the most recent listening events, newest first."""
    return ListeningEventRepository(session).list_recent(limit=limit)
