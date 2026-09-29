from datetime import UTC, datetime

import pytest

from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.recommendation.contextual_novelty import ContextualNoveltyRecommender
from soundmind.recommendation.fusion import CandidateSignals, FusionWeights


NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def test_contextual_novelty_affects_m1_ranking() -> None:
    candidates = [
        CandidateSignals("seen"),
        CandidateSignals("unseen"),
    ]
    events = [ListeningEvent("seen", ListeningEventType.PLAY, NOW, context="coding")]
    weights = FusionWeights(
        metadata=0.0,
        dsp=0.0,
        learned=0.0,
        preference=0.0,
        novelty=1.0,
        diversity=0.0,
    )

    ranked = ContextualNoveltyRecommender(weights=weights).rank(
        candidates,
        events,
        context="coding",
        now=NOW,
        limit=2,
    )

    assert [item.track_id for item in ranked] == ["unseen", "seen"]
    assert ranked[0].signals.novelty_score == pytest.approx(1.0)
    assert ranked[1].signals.novelty_score == pytest.approx(0.5)


def test_unseen_candidate_gets_maximum_contextual_novelty() -> None:
    candidates = [CandidateSignals("unseen", novelty_score=0.2)]
    events = [ListeningEvent("other", ListeningEventType.PLAY, NOW, context="coding")]

    ranked = ContextualNoveltyRecommender().rank(
        candidates,
        events,
        context="coding",
        now=NOW,
    )

    assert ranked[0].signals.novelty_score == pytest.approx(1.0)


def test_contextual_novelty_preserves_other_m1_signals() -> None:
    candidate = CandidateSignals(
        "a",
        metadata_score=0.2,
        dsp_score=0.3,
        learned_score=0.4,
        preference_score=0.5,
        novelty_score=0.1,
        diversity_score=0.6,
    )

    ranked = ContextualNoveltyRecommender().rank(
        [candidate],
        [ListeningEvent("a", ListeningEventType.PLAY, NOW, context="coding")],
        context="coding",
        now=NOW,
    )

    signals = ranked[0].signals
    assert signals.metadata_score == pytest.approx(0.2)
    assert signals.dsp_score == pytest.approx(0.3)
    assert signals.learned_score == pytest.approx(0.4)
    assert signals.preference_score == pytest.approx(0.5)
    assert signals.novelty_score == pytest.approx(0.5)
    assert signals.diversity_score == pytest.approx(0.6)


def test_context_isolated_from_other_contexts() -> None:
    candidates = [CandidateSignals("coding"), CandidateSignals("gym")]
    events = [ListeningEvent("coding", ListeningEventType.PLAY, NOW, context="coding")]

    ranked = ContextualNoveltyRecommender().rank(
        candidates,
        events,
        context="gym",
        now=NOW,
        limit=2,
    )

    by_id = {item.track_id: item for item in ranked}
    assert by_id["coding"].signals.novelty_score == pytest.approx(1.0)
    assert by_id["gym"].signals.novelty_score == pytest.approx(1.0)


def test_context_matching_is_normalized() -> None:
    ranked = ContextualNoveltyRecommender().rank(
        [CandidateSignals("a")],
        [ListeningEvent("a", ListeningEventType.PLAY, NOW, context=" Coding ")],
        context="CODING",
        now=NOW,
    )

    assert ranked[0].signals.novelty_score == pytest.approx(0.5)


def test_contextual_novelty_ranking_does_not_mutate_candidates() -> None:
    candidate = CandidateSignals("a", novelty_score=0.2)
    candidates = [candidate]

    ContextualNoveltyRecommender().rank(
        candidates,
        [ListeningEvent("a", ListeningEventType.PLAY, NOW, context="coding")],
        context="coding",
        now=NOW,
    )

    assert candidates == [candidate]


def test_contextual_novelty_ranking_is_deterministic() -> None:
    candidates = [CandidateSignals("b"), CandidateSignals("a")]
    events = [
        ListeningEvent("a", ListeningEventType.PLAY, NOW, context="coding"),
        ListeningEvent("a", ListeningEventType.REPLAY, NOW, context="coding"),
    ]
    recommender = ContextualNoveltyRecommender()

    first = recommender.rank(candidates, events, context="coding", now=NOW, limit=2)
    second = recommender.rank(candidates, events, context="coding", now=NOW, limit=2)

    assert first == second


def test_contextual_novelty_requires_non_empty_context() -> None:
    with pytest.raises(ValueError, match="context must be non-empty"):
        ContextualNoveltyRecommender().rank(
            [CandidateSignals("a")],
            [],
            context="   ",
            now=NOW,
        )


def test_contextual_novelty_requires_timezone_aware_reference_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ContextualNoveltyRecommender().rank(
            [CandidateSignals("a")],
            [ListeningEvent("a", ListeningEventType.PLAY, NOW, context="coding")],
            context="coding",
            now=datetime(2026, 9, 29, 12, 0),  # noqa: DTZ001
        )
