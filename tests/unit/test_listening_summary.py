from datetime import UTC, datetime

from soundmind.listening_summary import summarize_listening_events
from soundmind.preferences.models import ListeningEvent, ListeningEventType

NOW = datetime(2026, 10, 26, 7, 0, tzinfo=UTC)


def event(
    track_id: str,
    event_type: ListeningEventType,
    *,
    context: str | None,
) -> ListeningEvent:
    return ListeningEvent(track_id, event_type, NOW, context)


def test_summary_counts_types_tracks_and_normalizes_contexts() -> None:
    events = [
        event("track-a", ListeningEventType.LIKE, context="Coding"),
        event("track-a", ListeningEventType.SKIP, context=" coding "),
        event("track-b", ListeningEventType.DISLIKE, context=None),
        event("track-c", ListeningEventType.REPLAY, context=" Gym "),
        event("track-c", ListeningEventType.COMPLETE, context="gym"),
    ]

    summary = summarize_listening_events(events)

    assert summary.total_events == 5
    assert summary.distinct_tracks == 3
    assert dict(summary.event_type_counts) == {
        ListeningEventType.PLAY: 0,
        ListeningEventType.COMPLETE: 1,
        ListeningEventType.SKIP: 1,
        ListeningEventType.LIKE: 1,
        ListeningEventType.DISLIKE: 1,
        ListeningEventType.REPLAY: 1,
    }
    assert [
        (item.context, item.event_count, item.distinct_tracks)
        for item in summary.contexts
    ] == [
        ("coding", 2, 1),
        ("gym", 2, 1),
        (None, 1, 1),
    ]


def test_empty_summary_has_zero_counts_and_no_contexts() -> None:
    summary = summarize_listening_events([])

    assert summary.total_events == 0
    assert summary.distinct_tracks == 0
    assert dict(summary.event_type_counts) == {
        event_type: 0 for event_type in ListeningEventType
    }
    assert summary.contexts == ()


def test_summary_output_data_is_deterministic_for_same_events() -> None:
    events = [
        event("track-b", ListeningEventType.SKIP, context="Workout"),
        event("track-a", ListeningEventType.LIKE, context="coding"),
        event("track-c", ListeningEventType.PLAY, context=None),
    ]

    assert summarize_listening_events(events) == summarize_listening_events(events)
