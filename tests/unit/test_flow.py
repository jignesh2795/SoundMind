import pytest

from soundmind.flow import EndToEndCandidate, EndToEndMusicFlow, EndToEndRequest
from soundmind.intent import MusicIntent
from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.sequence import SequenceMode


def candidate(track_id: str, **kwargs) -> EndToEndCandidate:
    return EndToEndCandidate(IntentCandidate(track_id=track_id, **kwargs))


def test_end_to_end_flow_connects_intent_retrieval_ranking_and_sequence() -> None:
    request = EndToEndRequest(
        text="dark South Indian BGM for a hero entry, instrumental",
        candidates=[
            candidate(
                "b",
                moods=("dark",),
                regions=("south_india",),
                music_types=("bgm",),
                scenes=("hero_entry",),
                vocal_preference="instrumental",
                energy=0.7,
            ),
            candidate(
                "a",
                moods=("dark",),
                regions=("south_india",),
                music_types=("bgm",),
                scenes=("hero_entry",),
                vocal_preference="instrumental",
                energy=0.8,
            ),
            candidate("c", moods=("happy",), music_types=("song",), energy=0.5),
        ],
        mode=SequenceMode.SMOOTH,
        limit=2,
    )

    result = EndToEndMusicFlow().run(request)

    assert result.intent.moods == ("dark",)
    assert result.intent.regions == ("south_india",)
    assert [item.track_id for item in result.ranked] == ["a", "b"]
    assert [item.track_id for item in result.playlist] == ["a", "b"]


def test_end_to_end_flow_preserves_existing_m1_signals() -> None:
    item = IntentCandidate(
        "a",
        moods=("dark",),
        music_types=("bgm",),
        base_signals=CandidateSignals("a", learned_score=0.8, preference_score=0.4),
    )

    result = EndToEndMusicFlow().run(
        EndToEndRequest(text="dark BGM", candidates=[EndToEndCandidate(item)], limit=1)
    )

    assert result.ranked[0].signals.learned_score == pytest.approx(0.8)
    assert result.ranked[0].signals.preference_score == pytest.approx(0.4)


def test_end_to_end_flow_supports_journey_sequence() -> None:
    result = EndToEndMusicFlow().run(
        EndToEndRequest(
            text="high energy BGM",
            candidates=[
                candidate("a", music_types=("bgm",), energy=0.3),
                candidate("b", music_types=("bgm",), energy=0.6),
                candidate("c", music_types=("bgm",), energy=0.9),
            ],
            mode=SequenceMode.JOURNEY,
            limit=3,
        )
    )

    assert [item.track_id for item in result.playlist] == ["a", "b", "c"]


def test_end_to_end_flow_is_deterministic() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[
            candidate("b", moods=("dark",), music_types=("bgm",), energy=0.6),
            candidate("a", moods=("dark",), music_types=("bgm",), energy=0.6),
        ],
        limit=2,
    )

    first = EndToEndMusicFlow().run(request)
    second = EndToEndMusicFlow().run(request)

    assert first == second


def test_end_to_end_flow_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="text must be non-empty"):
        EndToEndMusicFlow().run(
            EndToEndRequest(text="   ", candidates=[candidate("a")])
        )


def test_end_to_end_flow_does_not_mutate_candidates() -> None:
    item = IntentCandidate(
        "a",
        moods=("dark",),
        music_types=("bgm",),
        base_signals=CandidateSignals("a", learned_score=0.5),
    )
    wrapped = EndToEndCandidate(item)

    EndToEndMusicFlow().run(
        EndToEndRequest(text="dark BGM", candidates=[wrapped], limit=1)
    )

    assert wrapped.intent_candidate == item


def test_end_to_end_flow_returns_empty_playlist_for_empty_catalog() -> None:
    result = EndToEndMusicFlow().run(
        EndToEndRequest(text="dark BGM", candidates=[], limit=10)
    )

    assert result.ranked == ()
    assert result.playlist == ()


def test_end_to_end_flow_rejects_duplicate_candidate_ids() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[candidate("a"), candidate("a")],
    )

    with pytest.raises(ValueError, match="duplicate track_id"):
        EndToEndMusicFlow().run(request)


def test_end_to_end_flow_maps_sequence_metadata_without_deriving_it() -> None:
    request = EndToEndRequest(
        text="dark BGM",
        candidates=[
            EndToEndCandidate(
                IntentCandidate("a", moods=("dark",), music_types=("bgm",), energy=0.5),
                tempo_bpm=90.0,
                brightness=0.2,
            ),
            EndToEndCandidate(
                IntentCandidate("b", moods=("dark",), music_types=("bgm",), energy=0.5),
                tempo_bpm=180.0,
                brightness=0.8,
            ),
        ],
        mode=SequenceMode.SMOOTH,
        limit=2,
    )

    result = EndToEndMusicFlow().run(request)

    assert [item.track_id for item in result.playlist] == ["a", "b"]


def test_end_to_end_result_exposes_parsed_music_intent() -> None:
    result = EndToEndMusicFlow().run(
        EndToEndRequest(
            text="Tamil emotional BGM",
            candidates=[candidate("a", languages=("tamil",), moods=("emotional",))],
            limit=1,
        )
    )

    assert isinstance(result.intent, MusicIntent)
    assert result.intent.languages == ("tamil",)
    assert result.intent.music_types == ("bgm",)
