"""Read-only summaries of persisted listening feedback."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from soundmind.preferences.models import ListeningEvent, ListeningEventType


@dataclass(frozen=True)
class ListeningContextSummary:
    """Counts for one normalized listening context."""

    context: str | None
    event_count: int
    distinct_tracks: int


@dataclass(frozen=True)
class ListeningEventSummary:
    """Deterministic summary of a bounded set of listening events."""

    total_events: int
    distinct_tracks: int
    event_type_counts: tuple[tuple[ListeningEventType, int], ...]
    contexts: tuple[ListeningContextSummary, ...]


def summarize_listening_events(
    events: Iterable[ListeningEvent],
) -> ListeningEventSummary:
    """Aggregate event types and normalized contexts without mutating events."""
    materialized = tuple(events)
    event_counts = Counter(event.event_type for event in materialized)
    context_event_counts: Counter[str | None] = Counter()
    context_tracks: dict[str | None, set[str]] = defaultdict(set)

    for event in materialized:
        normalized_context = (
            event.context.strip().lower() if event.context is not None else ""
        )
        context = normalized_context or None
        context_event_counts[context] += 1
        context_tracks[context].add(event.track_id)

    contexts = tuple(
        ListeningContextSummary(
            context=context,
            event_count=context_event_counts[context],
            distinct_tracks=len(context_tracks[context]),
        )
        for context in sorted(
            context_event_counts,
            key=lambda value: (value is None, value or ""),
        )
    )
    event_type_counts = tuple(
        (event_type, event_counts[event_type])
        for event_type in ListeningEventType
    )
    return ListeningEventSummary(
        total_events=len(materialized),
        distinct_tracks=len({event.track_id for event in materialized}),
        event_type_counts=event_type_counts,
        contexts=contexts,
    )
