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
