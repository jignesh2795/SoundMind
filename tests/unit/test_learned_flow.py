import pytest

from soundmind.flow import EndToEndCandidate, EndToEndRequest
from soundmind.intent import parse_intent
from soundmind.learned_flow import LearnedEndToEndMusicFlow
from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine
from soundmind.sequence import SequenceMode
from soundmind.vector.index import SimilarityResult


class FakeSimilarityProvider:
    def similar(self, track_id: str, *, limit: int = 10):
        assert track_id == "seed"
        return [
            SimilarityResult("b", 0.9),
            SimilarityResult("a", 0.1),
            SimilarityResult("seed", 1.0),
        ][:limit]


def candidate(track_id: str, *, learned_score: float = 0.0) -> EndToEndCandidate:
    return EndToEndCandidate(
        IntentCandidate(
            track_id=track_id,
            moods=("dark",),
            music_types=("bgm",),
            base_signals=CandidateSignals(track_id, learned_score=learned_score),
        ),
        tempo_bpm=100.0,
        brightness=0.5,
    )


def test_learned_flow_uses_similarity_in_existing_m1_ranking() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("seed"), candidate("a"), candidate("b")],
        mode=SequenceMode.SMOOTH,
        limit=2,
    )
    flow = LearnedEndToEndMusicFlow(
        LearnedRetrievalEngine(FakeSimilarityProvider())
    )

    result = flow.run(request, seed_track_id="seed")

    assert [item.track_id for item in result.ranked] == ["b", "a"]
    assert result.ranked[0].signals.learned_score == pytest.approx(0.95)
    assert result.ranked[1].signals.learned_score == pytest.approx(0.55)
    assert [item.track_id for item in result.playlist] == ["b", "a"]


def test_learned_flow_excludes_seed_without_mutating_request() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("seed"), candidate("a")],
        limit=2,
    )
    original = tuple(request.candidates)
    flow = LearnedEndToEndMusicFlow(
        LearnedRetrievalEngine(FakeSimilarityProvider())
    )

    result = flow.run(request, seed_track_id="seed")

    assert result.ranked[0].track_id == "a"
    assert tuple(request.candidates) == original
    assert request.candidates[0].intent_candidate.track_id == "seed"


def test_learned_flow_preserves_m5_intent_and_sequence_contracts() -> None:
    request = EndToEndRequest(
        text="Tamil dark BGM",
        candidates=[
            EndToEndCandidate(
                IntentCandidate(
                    "seed",
                    languages=("tamil",),
                    moods=("dark",),
                    music_types=("bgm",),
                )
            ),
            EndToEndCandidate(
                IntentCandidate(
                    "a",
                    languages=("tamil",),
                    moods=("dark",),
                    music_types=("bgm",),
                    energy=0.5,
                ),
                tempo_bpm=90.0,
                brightness=0.4,
            ),
        ],
        mode=SequenceMode.SMOOTH,
        limit=1,
    )
    flow = LearnedEndToEndMusicFlow(
        LearnedRetrievalEngine(FakeSimilarityProvider())
    )

    result = flow.run(request, seed_track_id="seed")

    assert result.intent == parse_intent("Tamil dark BGM")
    assert len(result.playlist) == 1
    assert result.playlist[0].track_id == "a"
