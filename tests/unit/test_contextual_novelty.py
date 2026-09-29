from datetime import UTC, datetime, timedelta

import pytest

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.preferences.novelty import ContextualNoveltyScorer

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def event(
    track_id: str,
    event_type: ListeningEventType,
    *,
    days_ago: float = 0.0,
    context: str | None = None,
) -> ListeningEvent:
    return ListeningEvent(
        track_id=track_id,
        event_type=event_type,
        occurred_at=NOW - timedelta(days=days_ago),
        context=context,
    )


def test_unexposed_track_has_maximum_novelty() -> None:
    result = ContextualNoveltyScorer().score_events(
        [event("other", ListeningEventType.PLAY, context="coding")],
        context="coding",
        now=NOW,
    )

    assert "unheard" not in result


def test_single_recent_exposure_has_half_novelty() -> None:
    result = ContextualNoveltyScorer().score_events(
        [event("a", ListeningEventType.PLAY, context="coding")],
        context="coding",
        now=NOW,
    )

    assert result["a"] == pytest.approx(0.5)


def test_repeated_exposure_reduces_novelty() -> None:
    result = ContextualNoveltyScorer().score_events(
        [
            event("a", ListeningEventType.PLAY, context="coding"),
            event("a", ListeningEventType.COMPLETE, context="coding"),
        ],
        context="coding",
        now=NOW,
    )

    assert result["a"] == pytest.approx(1.0 / 3.0)


def test_all_existing_event_types_count_as_exposure() -> None:
    events = [
        event("play", ListeningEventType.PLAY, context="coding"),
        event("complete", ListeningEventType.COMPLETE, context="coding"),
        event("skip", ListeningEventType.SKIP, context="coding"),
        event("like", ListeningEventType.LIKE, context="coding"),
        event("dislike", ListeningEventType.DISLIKE, context="coding"),
        event("replay", ListeningEventType.REPLAY, context="coding"),
    ]

    result = ContextualNoveltyScorer().score_events(events, context="coding", now=NOW)

    assert all(result[track_id] == pytest.approx(0.5) for track_id in (
        "play",
        "complete",
        "skip",
        "like",
        "dislike",
        "replay",
    ))


def test_older_exposure_is_less_familiar_than_recent_exposure() -> None:
    result = ContextualNoveltyScorer().score_events(
        [
            event("recent", ListeningEventType.PLAY, context="coding"),
            event("old", ListeningEventType.PLAY, context="coding", days_ago=30.0),
        ],
        context="coding",
        now=NOW,
    )

    assert result["recent"] < result["old"]


def test_contextual_novelty_is_isolated() -> None:
    result = ContextualNoveltyScorer().score_events(
        [
            event("coding-track", ListeningEventType.PLAY, context="coding"),
            event("gym-track", ListeningEventType.PLAY, context="gym"),
            event("global-track", ListeningEventType.PLAY),
        ],
        context="coding",
        now=NOW,
    )

    assert "coding-track" in result
    assert "gym-track" not in result
    assert "global-track" not in result


def test_context_matching_is_normalized() -> None:
    result = ContextualNoveltyScorer().score_events(
        [event("a", ListeningEventType.PLAY, context=" Coding ")],
        context="CODING",
        now=NOW,
    )

    assert result["a"] == pytest.approx(0.5)


def test_empty_context_has_no_novelty_evidence() -> None:
    scorer = ContextualNoveltyScorer()
    events = [event("a", ListeningEventType.PLAY, context="coding")]

    assert scorer.score_events(events, context=None, now=NOW) == {}
    assert scorer.score_events(events, context="   ", now=NOW) == {}


def test_contextual_novelty_requires_timezone_aware_times() -> None:
    scorer = ContextualNoveltyScorer()
    with pytest.raises(ValueError, match="timezone-aware"):
        scorer.score_events(
            [event("a", ListeningEventType.PLAY, context="coding")],
            context="coding",
            now=datetime(2026, 9, 29, 12, 0),  # noqa: DTZ001
        )
