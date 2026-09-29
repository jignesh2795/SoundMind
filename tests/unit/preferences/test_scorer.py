from datetime import UTC, datetime, timedelta

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.preferences.scorer import PreferenceScorer


def event(track_id, kind, days=0):
    return ListeningEvent(track_id, kind, datetime.now(UTC) - timedelta(days=days))

def test_like_is_positive_and_decay_applies():
    now = datetime.now(UTC)
    scores = PreferenceScorer().score_events([event("a", ListeningEventType.LIKE)], now=now)
    old = PreferenceScorer().score_events([event("b", ListeningEventType.LIKE, 30)], now=now)
    assert scores["a"] > old["b"] > 0

def test_dislike_and_skip_reduce_preference():
    now = datetime.now(UTC)
    scores = PreferenceScorer().score_events([event("a", ListeningEventType.DISLIKE), event("a", ListeningEventType.SKIP)], now=now)
    assert scores["a"] < 0

def test_unknown_track_has_no_preference_signal():
    now = datetime.now(UTC)
    scores = PreferenceScorer().score_events([event("liked", ListeningEventType.LIKE)], now=now)
    assert scores.get("unseen", 0.0) == 0.0
