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
