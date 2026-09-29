import pytest

from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine
from soundmind.vector.index import SimilarityResult


class FakeSimilarityProvider:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def similar(self, track_id: str, *, limit: int = 10):
        self.calls.append((track_id, limit))
        return list(self.results)


def candidate(track_id: str, *, learned_score: float = 0.0) -> IntentCandidate:
    return IntentCandidate(
        track_id=track_id,
        base_signals=CandidateSignals(
            track_id,
            metadata_score=0.2,
            dsp_score=0.3,
            learned_score=learned_score,
            preference_score=0.4,
            novelty_score=0.5,
            diversity_score=0.6,
        ),
    )


def test_enrich_maps_cosine_similarity_into_learned_score() -> None:
    provider = FakeSimilarityProvider(
        [
            SimilarityResult("b", 1.0),
            SimilarityResult("c", 0.0),
            SimilarityResult("outside", 0.9),
        ]
    )
    engine = LearnedRetrievalEngine(provider)

    result = engine.enrich("seed", [candidate("b"), candidate("c"), candidate("d")])

    assert [item.track_id for item in result] == ["b", "c", "d"]
    assert result[0].base_signals.learned_score == pytest.approx(1.0)
    assert result[1].base_signals.learned_score == pytest.approx(0.5)
    assert result[2].base_signals.learned_score == 0.0


def test_enrich_preserves_other_m1_signals_and_does_not_mutate() -> None:
    original = candidate("b", learned_score=0.25)
    provider = FakeSimilarityProvider([SimilarityResult("b", 0.5)])
    result = LearnedRetrievalEngine(provider).enrich("seed", [original])

    enriched = result[0]
    assert enriched is not original
    assert enriched.base_signals is not original.base_signals
    assert enriched.base_signals.metadata_score == 0.2
    assert enriched.base_signals.dsp_score == 0.3
    assert enriched.base_signals.preference_score == 0.4
    assert enriched.base_signals.novelty_score == 0.5
    assert enriched.base_signals.diversity_score == 0.6
    assert enriched.base_signals.learned_score == pytest.approx(0.75)
    assert original.base_signals.learned_score == 0.25


def test_enrich_keeps_existing_score_when_candidate_has_no_similarity() -> None:
    provider = FakeSimilarityProvider([SimilarityResult("outside", 1.0)])
    result = LearnedRetrievalEngine(provider).enrich(
        "seed",
        [candidate("a", learned_score=0.35)],
    )

    assert result[0].base_signals.learned_score == pytest.approx(0.35)


def test_enrich_ignores_seed_and_unknown_similarity_results() -> None:
    provider = FakeSimilarityProvider(
        [SimilarityResult("seed", 1.0), SimilarityResult("outside", 1.0)]
    )
    result = LearnedRetrievalEngine(provider).enrich("seed", [candidate("a")])

    assert result[0].base_signals.learned_score == 0.0


def test_enrich_rejects_duplicate_candidates() -> None:
    provider = FakeSimilarityProvider([])
    with pytest.raises(ValueError, match="duplicate track_id"):
        LearnedRetrievalEngine(provider).enrich(
            "seed",
            [candidate("a"), candidate("a")],
        )


def test_enrich_rejects_invalid_seed_and_limit() -> None:
    provider = FakeSimilarityProvider([])
    engine = LearnedRetrievalEngine(provider)

    with pytest.raises(ValueError, match="seed_track_id"):
        engine.enrich("", [candidate("a")])

    with pytest.raises(ValueError, match="limit"):
        engine.enrich("seed", [candidate("a")], limit=0)


def test_enrich_is_deterministic_and_requests_enough_results() -> None:
    provider = FakeSimilarityProvider([SimilarityResult("b", 0.8)])
    engine = LearnedRetrievalEngine(provider)

    first = engine.enrich("seed", [candidate("a"), candidate("b")], limit=2)
    second = engine.enrich("seed", [candidate("a"), candidate("b")], limit=2)

    assert first == second
    assert provider.calls == [("seed", 2), ("seed", 2)]
