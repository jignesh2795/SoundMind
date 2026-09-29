from datetime import UTC, datetime, timedelta

import pytest

from soundmind.preferences.contextual import ContextualPreferenceScorer
from soundmind.preferences.models import ListeningEvent, ListeningEventType


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


def test_scores_only_events_for_requested_context() -> None:
    scorer = ContextualPreferenceScorer()

    result = scorer.score_events(
        [
            event("coding-track", ListeningEventType.LIKE, context="coding"),
            event("gym-track", ListeningEventType.LIKE, context="gym"),
            event("global-track", ListeningEventType.LIKE),
        ],
        context="coding",
        now=NOW,
    )

    assert result["coding-track"] == pytest.approx(0.462117)
    assert "gym-track" not in result
    assert "global-track" not in result


def test_context_matching_is_normalized() -> None:
    scorer = ContextualPreferenceScorer()

    result = scorer.score_events(
        [event("a", ListeningEventType.LIKE, context=" Coding ")],
        context="CODING",
        now=NOW,
    )

    assert result["a"] == pytest.approx(0.462117)


def test_positive_and_negative_context_events_are_bounded() -> None:
    scorer = ContextualPreferenceScorer()

    result = scorer.score_events(
        [
            event("a", ListeningEventType.LIKE, context="coding"),
            event("a", ListeningEventType.DISLIKE, context="coding"),
            event("a", ListeningEventType.REPLAY, context="coding"),
            event("a", ListeningEventType.SKIP, context="coding"),
        ],
        context="coding",
        now=NOW,
    )

    assert -1.0 <= result["a"] <= 1.0
    assert result["a"] > 0.0


def test_context_decay_matches_existing_half_life() -> None:
    scorer = ContextualPreferenceScorer(half_life_days=30.0)

    result = scorer.score_events(
        [event("a", ListeningEventType.LIKE, context="coding", days_ago=30.0)],
        context="coding",
        now=NOW,
    )

    assert result["a"] == pytest.approx(0.244919)


def test_empty_or_unknown_context_has_no_evidence() -> None:
    scorer = ContextualPreferenceScorer()

    assert (
        scorer.score_events(
            [event("a", ListeningEventType.LIKE, context="coding")],
            context=None,
            now=NOW,
        )
        == {}
    )
    assert (
        scorer.score_events(
            [event("a", ListeningEventType.LIKE, context="coding")],
            context="work",
            now=NOW,
        )
        == {}
    )


def test_context_requires_timezone_aware_reference_time() -> None:
    scorer = ContextualPreferenceScorer()

    with pytest.raises(ValueError, match="timezone-aware"):
        scorer.score_events(
            [event("a", ListeningEventType.LIKE, context="coding")],
            context="coding",
            now=datetime(2026, 9, 29, 12, 0),
        )
