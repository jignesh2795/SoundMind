from datetime import UTC, datetime

import pytest

from soundmind.context_aware_flow import ContextAwareMusicFlow
from soundmind.flow import EndToEndCandidate, EndToEndRequest
from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.recommendation.fusion import CandidateSignals, FusionWeights
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine
from soundmind.sequence import SequenceMode
from soundmind.vector.index import SimilarityResult

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


class FakeSimilarityProvider:
    def similar(self, track_id: str, *, limit: int = 10):
        assert track_id == "seed"
        return [
            SimilarityResult("b", 0.9),
            SimilarityResult("a", 0.1),
            SimilarityResult("seed", 1.0),
        ][:limit]


def candidate(
    track_id: str,
    *,
    learned_score: float = 0.0,
    preference_score: float = 0.0,
    novelty_score: float = 0.0,
) -> EndToEndCandidate:
    return EndToEndCandidate(
        IntentCandidate(
            track_id=track_id,
            moods=("dark",),
            music_types=("bgm",),
            base_signals=CandidateSignals(
                track_id,
                learned_score=learned_score,
                preference_score=preference_score,
                novelty_score=novelty_score,
            ),
        ),
        tempo_bpm=100.0,
        brightness=0.5,
    )


def test_context_aware_flow_composes_learned_preference_and_novelty() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("seed"), candidate("a"), candidate("b")],
        mode=SequenceMode.SMOOTH,
        limit=2,
    )
    flow = ContextAwareMusicFlow(
        learned=LearnedRetrievalEngine(FakeSimilarityProvider())
    )

    result = flow.run(
        request,
        events=[ListeningEvent("a", ListeningEventType.LIKE, NOW, context="coding")],
        context="coding",
        now=NOW,
        seed_track_id="seed",
    )

    assert [item.track_id for item in result.ranked] == ["b", "a"]
    assert result.ranked[0].signals.learned_score == pytest.approx(0.95)
    assert result.ranked[0].signals.preference_score == pytest.approx(0.0)
    assert result.ranked[0].signals.novelty_score == pytest.approx(1.0)
    assert result.ranked[1].signals.learned_score == pytest.approx(0.55)
    assert result.ranked[1].signals.preference_score > 0.0
    assert result.ranked[1].signals.novelty_score == pytest.approx(0.5)
    assert [item.track_id for item in result.playlist] == ["b", "a"]


def test_context_aware_flow_isolates_context() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("a"), candidate("b")],
        limit=2,
    )
    flow = ContextAwareMusicFlow()

    result = flow.run(
        request,
        events=[ListeningEvent("a", ListeningEventType.LIKE, NOW, context="coding")],
        context="gym",
        now=NOW,
    )

    by_id = {item.track_id: item for item in result.ranked}
    assert by_id["a"].signals.preference_score == pytest.approx(0.0)
    assert by_id["a"].signals.novelty_score == pytest.approx(1.0)
    assert by_id["b"].signals.preference_score == pytest.approx(0.0)
    assert by_id["b"].signals.novelty_score == pytest.approx(1.0)


def test_context_aware_flow_preserves_existing_candidate_signals() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[
            candidate(
                "a",
                learned_score=0.4,
                preference_score=0.3,
                novelty_score=0.2,
            )
        ],
        limit=1,
    )

    result = ContextAwareMusicFlow().run(
        request,
        events=[],
        context="coding",
        now=NOW,
    )

    signals = result.ranked[0].signals
    assert signals.learned_score == pytest.approx(0.4)
    assert signals.preference_score == pytest.approx(0.0)
    assert signals.novelty_score == pytest.approx(1.0)


def test_context_aware_flow_excludes_learned_seed_without_mutating_request() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("seed"), candidate("a")],
        limit=1,
    )
    original = tuple(request.candidates)
    flow = ContextAwareMusicFlow(
        learned=LearnedRetrievalEngine(FakeSimilarityProvider())
    )

    result = flow.run(
        request,
        events=[],
        context="coding",
        now=NOW,
        seed_track_id="seed",
    )

    assert [item.track_id for item in result.ranked] == ["a"]
    assert tuple(request.candidates) == original


def test_context_aware_flow_requires_learned_dependency_for_seed() -> None:
    with pytest.raises(ValueError, match="learned retrieval is required"):
        ContextAwareMusicFlow().run(
            EndToEndRequest(text="dark BGM", candidates=[candidate("a")], limit=1),
            events=[],
            context="coding",
            now=NOW,
            seed_track_id="seed",
        )


def test_context_aware_flow_reuses_explicit_fusion_weights() -> None:
    weights = FusionWeights(
        metadata=0.0,
        dsp=0.0,
        learned=0.0,
        preference=1.0,
        novelty=0.0,
        diversity=0.0,
    )
    request = EndToEndRequest(
        text="play something",
        candidates=[candidate("a"), candidate("b")],
        weights=weights,
        limit=2,
    )

    result = ContextAwareMusicFlow().run(
        request,
        events=[ListeningEvent("a", ListeningEventType.LIKE, NOW, context="coding")],
        context="coding",
        now=NOW,
    )

    assert [item.track_id for item in result.ranked] == ["a", "b"]


def test_context_aware_flow_is_deterministic() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("b"), candidate("a")],
        limit=2,
    )
    events = [ListeningEvent("a", ListeningEventType.PLAY, NOW, context="coding")]
    flow = ContextAwareMusicFlow()

    first = flow.run(request, events=events, context="coding", now=NOW)
    second = flow.run(request, events=events, context="coding", now=NOW)

    assert first == second


def test_context_aware_flow_carries_contextual_novelty_into_discovery_sequence() -> None:
    weights = FusionWeights(
        metadata=0.0,
        dsp=0.0,
        learned=0.0,
        preference=0.0,
        novelty=1.0,
        diversity=0.0,
    )
    request = EndToEndRequest(
        text="play something",
        candidates=[candidate("seen"), candidate("new")],
        mode=SequenceMode.DISCOVERY,
        weights=weights,
        limit=2,
    )

    result = ContextAwareMusicFlow().run(
        request,
        events=[ListeningEvent("seen", ListeningEventType.PLAY, NOW, context="coding")],
        context="coding",
        now=NOW,
    )

    assert [item.track_id for item in result.ranked] == ["new", "seen"]
    assert [item.track_id for item in result.playlist] == ["new", "seen"]
