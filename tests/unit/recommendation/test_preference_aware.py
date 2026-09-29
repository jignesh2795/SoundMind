from datetime import UTC, datetime

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.preference_aware import PreferenceAwareRecommender


def test_preference_is_applied_before_fusion():
    now = datetime.now(UTC)
    events = [ListeningEvent("liked", ListeningEventType.LIKE, now)]
    candidates = [CandidateSignals("liked"), CandidateSignals("new")]
    ranked = PreferenceAwareRecommender().rank(candidates, events, now=now, limit=2)
    assert ranked[0].track_id == "liked"
    assert ranked[0].signals.preference_score > 0
    assert ranked[1].signals.preference_score == 0


def test_contextual_preference_replaces_global_preference_at_boundary():
    now = datetime.now(UTC)
    events = [
        ListeningEvent("coding", ListeningEventType.LIKE, now, context="coding"),
        ListeningEvent("global", ListeningEventType.LIKE, now),
    ]
    candidates = [
        CandidateSignals("coding", learned_score=0.1),
        CandidateSignals("global", learned_score=0.1),
    ]

    ranked = PreferenceAwareRecommender().rank(
        candidates,
        events,
        now=now,
        context="coding",
        limit=2,
    )

    assert ranked[0].track_id == "coding"
    assert ranked[0].signals.preference_score > 0
    assert ranked[0].signals.learned_score == 0.1
    assert ranked[1].signals.preference_score == 0


def test_contextual_ranking_does_not_mutate_candidates():
    now = datetime.now(UTC)
    candidate = CandidateSignals("coding")
    candidates = [candidate]

    PreferenceAwareRecommender().rank(
        candidates,
        [ListeningEvent("coding", ListeningEventType.LIKE, now, context="coding")],
        now=now,
        context="coding",
    )

    assert candidates == [candidate]
