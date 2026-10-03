import pytest

from soundmind.intent import MusicIntent, parse_intent
from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import (
    IntentCandidate,
    IntentRetrievalEngine,
)


def candidate(track_id: str, **kwargs) -> IntentCandidate:
    return IntentCandidate(track_id=track_id, **kwargs)


def test_full_structured_match_scores_one():
    intent = parse_intent("dark South Indian BGM for a hero entry, instrumental")
    item = candidate(
        "a",
        moods=("dark",),
        regions=("south_india",),
        music_types=("bgm",),
        scenes=("hero_entry",),
        vocal_preference="instrumental",
    )

    match = IntentRetrievalEngine().score(intent, item)

    assert match.intent_score == pytest.approx(1.0)


def test_unspecified_dimensions_do_not_penalize_candidate():
    intent = parse_intent("dark BGM")
    item = candidate("a", moods=("dark",), music_types=("bgm",), languages=())

    assert IntentRetrievalEngine().score(intent, item).intent_score == pytest.approx(1.0)


def test_energy_similarity_is_linear():
    intent = MusicIntent(raw_text="high energy", energy=0.8, confidence=0.2)
    item = candidate("a", energy=0.6)

    assert IntentRetrievalEngine().score(intent, item).energy_score == pytest.approx(0.8)


def test_conflicting_vocal_preference_scores_zero():
    intent = parse_intent("instrumental BGM")
    item = candidate("a", music_types=("bgm",), vocal_preference="vocal")

    match = IntentRetrievalEngine().score(intent, item)

    assert match.vocal_score == pytest.approx(0.0)


def test_unknown_vocal_preference_is_partial_match():
    intent = parse_intent("instrumental BGM")
    item = candidate("a", music_types=("bgm",))

    assert IntentRetrievalEngine().score(intent, item).vocal_score == pytest.approx(0.5)


def test_discovery_uses_candidate_novelty():
    intent = parse_intent("something new")
    item = candidate("a", novelty_score=0.75)

    assert IntentRetrievalEngine().score(intent, item).novelty_score == pytest.approx(0.75)


def test_familiar_uses_complement_of_novelty():
    intent = parse_intent("familiar music")
    item = candidate("a", novelty_score=0.75)

    assert IntentRetrievalEngine().score(intent, item).novelty_score == pytest.approx(0.25)


def test_no_structured_constraints_do_not_create_a_match():
    intent = parse_intent("play something")
    item = candidate("a", moods=("dark",), novelty_score=1.0)

    assert IntentRetrievalEngine().score(intent, item).intent_score == pytest.approx(0.0)


def test_enrich_maps_intent_to_m1_signals_without_overwriting_unowned_signals():
    intent = parse_intent("dark BGM")
    item = candidate(
        "a",
        moods=("dark",),
        music_types=("bgm",),
        base_signals=CandidateSignals("a", learned_score=0.8, preference_score=0.4),
    )

    signals = IntentRetrievalEngine().enrich(intent, item)

    assert signals.metadata_score == pytest.approx(1.0)
    assert signals.learned_score == pytest.approx(0.8)
    assert signals.preference_score == pytest.approx(0.4)


def test_energy_intent_maps_to_dsp_score():
    intent = MusicIntent(raw_text="high energy", energy=0.8, confidence=0.2)
    item = candidate("a", energy=0.6)

    signals = IntentRetrievalEngine().enrich(intent, item)

    assert signals.dsp_score == pytest.approx(0.8)


def test_rank_uses_existing_m1_fusion():
    intent = parse_intent("dark BGM")
    items = [
        candidate(
            "b",
            moods=("dark",),
            music_types=("bgm",),
            base_signals=CandidateSignals("b", learned_score=0.1),
        ),
        candidate(
            "a",
            moods=("dark",),
            music_types=("bgm",),
            base_signals=CandidateSignals("a", learned_score=0.1),
        ),
    ]

    ranked = IntentRetrievalEngine().rank(intent, items, limit=2)

    assert [item.track_id for item in ranked] == ["a", "b"]


def test_input_candidate_is_not_mutated():
    intent = parse_intent("dark BGM")
    base = CandidateSignals("a", learned_score=0.5)
    item = candidate("a", moods=("dark",), music_types=("bgm",), base_signals=base)

    IntentRetrievalEngine().enrich(intent, item)

    assert item.base_signals == base


def test_missing_candidate_energy_scores_partial():
    intent = MusicIntent(raw_text="high energy", energy=0.8, confidence=0.2)
    item = candidate("a")

    assert item.energy is None
    assert IntentRetrievalEngine().score(intent, item).energy_score == pytest.approx(0.5)


def test_negative_vocal_terms_score_by_candidate_preference():
    intent = MusicIntent(
        raw_text="dark BGM",
        vocal_preference="instrumental",
        negative_terms=("vocals",),
        confidence=0.5,
    )
    engine = IntentRetrievalEngine()

    assert engine.score(
        intent, candidate("a", vocal_preference="vocal")
    ).vocal_score == pytest.approx(0.0)
    assert engine.score(
        intent, candidate("b", vocal_preference="instrumental")
    ).vocal_score == pytest.approx(1.0)
    assert engine.score(intent, candidate("c")).vocal_score == pytest.approx(0.5)


def test_negative_vocal_terms_take_precedence_over_stated_preference():
    intent = MusicIntent(
        raw_text="dark BGM",
        vocal_preference="vocal",
        negative_terms=("vocals",),
        confidence=0.5,
    )

    assert IntentRetrievalEngine().score(
        intent, candidate("a", vocal_preference="vocal")
    ).vocal_score == pytest.approx(0.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"track_id": ""},
        {"track_id": "a", "energy": 1.5},
        {"track_id": "a", "novelty_score": -0.1},
        {"track_id": "a", "vocal_preference": "loud"},
    ],
)
def test_candidate_validation_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        IntentCandidate(**kwargs)


def test_enrich_many_matches_individual_enrich():
    intent = parse_intent("dark BGM")
    items = [
        candidate("a", moods=("dark",)),
        candidate("b", music_types=("bgm",)),
    ]
    engine = IntentRetrievalEngine()

    assert engine.enrich_many(intent, items) == [engine.enrich(intent, item) for item in items]


def test_any_vocal_preference_preserves_signals():
    intent = parse_intent("dark BGM")
    base = CandidateSignals(
        "a",
        metadata_score=0.9,
        dsp_score=0.6,
        learned_score=0.7,
        preference_score=0.3,
        novelty_score=0.4,
        diversity_score=0.2,
    )
    item = candidate("a", moods=("dark",), music_types=("bgm",), base_signals=base)

    signals = IntentRetrievalEngine().enrich(intent, item)

    assert "vocal_preference" not in IntentRetrievalEngine().score(intent, item).matched_dimensions
    assert "novelty" not in IntentRetrievalEngine().score(intent, item).matched_dimensions
    assert signals.learned_score == pytest.approx(0.7)
    assert signals.preference_score == pytest.approx(0.3)
    assert signals.diversity_score == pytest.approx(0.2)
    assert signals.dsp_score == pytest.approx(0.6)
    assert signals.novelty_score == pytest.approx(0.4)


def test_any_novelty_preserves_base_novelty_score():
    intent = MusicIntent(raw_text="high energy", energy=0.8, confidence=0.2)
    item = candidate("a", energy=0.6, base_signals=CandidateSignals("a", novelty_score=0.4))

    match = IntentRetrievalEngine().score(intent, item)
    signals = IntentRetrievalEngine().enrich(intent, item)

    assert "novelty" not in match.matched_dimensions
    assert signals.novelty_score == pytest.approx(0.4)
    assert signals.dsp_score == pytest.approx(0.8)


def test_enrich_preserves_diversity_and_unrequested_dimensions():
    intent = MusicIntent(raw_text="dark", moods=("dark",), confidence=0.5)
    base = CandidateSignals(
        "a",
        dsp_score=0.6,
        learned_score=0.7,
        preference_score=0.3,
        novelty_score=0.4,
        diversity_score=0.25,
    )
    item = candidate("a", moods=("dark",), base_signals=base)

    signals = IntentRetrievalEngine().enrich(intent, item)

    assert signals.metadata_score == pytest.approx(1.0)
    assert signals.dsp_score == pytest.approx(0.6)
    assert signals.learned_score == pytest.approx(0.7)
    assert signals.preference_score == pytest.approx(0.3)
    assert signals.novelty_score == pytest.approx(0.4)
    assert signals.diversity_score == pytest.approx(0.25)


def test_score_and_rank_are_repeatable():
    intent = parse_intent("dark BGM")
    items = [
        candidate("b", moods=("dark",)),
        candidate("a", moods=("dark",)),
    ]
    engine = IntentRetrievalEngine()

    assert engine.score(intent, items[0]) == engine.score(intent, items[0])
    assert engine.rank(intent, items, limit=2) == engine.rank(intent, items, limit=2)
