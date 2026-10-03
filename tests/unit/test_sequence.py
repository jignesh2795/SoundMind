import math
from itertools import pairwise

import pytest

from soundmind.sequence import (
    SequenceCandidate,
    SequenceMode,
    SequenceRequest,
    journey_target_energy,
    sequence_playlist,
)


def candidate(
    track_id: str,
    score: float,
    *,
    energy: float = 0.5,
    tempo_bpm: float = 120.0,
    brightness: float = 0.5,
    novelty: float = 0.0,
) -> SequenceCandidate:
    return SequenceCandidate(
        track_id=track_id,
        base_score=score,
        energy=energy,
        tempo_bpm=tempo_bpm,
        brightness=brightness,
        novelty_score=novelty,
    )


def test_smooth_prefers_small_transition_distance():
    request = SequenceRequest(
        candidates=(
            candidate("seed", 1.0, energy=0.5, tempo_bpm=120, brightness=0.5),
            candidate("near", 0.8, energy=0.52, tempo_bpm=122, brightness=0.51),
            candidate("far", 0.95, energy=0.95, tempo_bpm=180, brightness=0.95),
        ),
        mode=SequenceMode.SMOOTH,
        seed_track_id="seed",
        limit=3,
    )
    result = sequence_playlist(request)
    assert [item.track_id for item in result] == ["seed", "near", "far"]


def test_contrast_prefers_larger_transition_distance():
    request = SequenceRequest(
        candidates=(
            candidate("seed", 1.0, energy=0.5, tempo_bpm=120, brightness=0.5),
            candidate("near", 0.95, energy=0.52, tempo_bpm=122, brightness=0.51),
            candidate("far", 0.7, energy=0.95, tempo_bpm=180, brightness=0.95),
        ),
        mode=SequenceMode.CONTRAST,
        seed_track_id="seed",
        limit=3,
    )
    result = sequence_playlist(request)
    assert [item.track_id for item in result] == ["seed", "far", "near"]


def test_journey_target_energy_is_explicit_and_monotonic():
    targets = tuple(journey_target_energy(position, 5) for position in range(5))
    assert targets == (0.3, 0.45, 0.6, 0.75, 0.9)
    assert all(left < right for left, right in pairwise(targets))


def test_journey_moves_through_explicit_energy_arc():
    request = SequenceRequest(
        candidates=(
            candidate("low", 0.9, energy=0.2),
            candidate("mid", 0.8, energy=0.5),
            candidate("high", 0.7, energy=0.9),
        ),
        mode=SequenceMode.JOURNEY,
        limit=3,
    )
    result = sequence_playlist(request)
    assert [item.track_id for item in result] == ["low", "mid", "high"]


def test_discovery_uses_supplied_novelty_without_overriding_relevance():
    request = SequenceRequest(
        candidates=(
            candidate("familiar", 1.0, novelty=0.0),
            candidate("discovery", 0.8, novelty=1.0),
        ),
        mode=SequenceMode.DISCOVERY,
        limit=2,
    )
    result = sequence_playlist(request)
    assert [item.track_id for item in result] == ["familiar", "discovery"]


def test_seed_must_exist():
    request = SequenceRequest(
        candidates=(candidate("a", 1.0),),
        seed_track_id="missing",
        limit=1,
    )
    with pytest.raises(ValueError, match="seed_track_id"):
        sequence_playlist(request)


@pytest.mark.parametrize(
    "candidates",
    [
        (candidate("", 1.0),),
        (candidate("a", 1.0), candidate("a", 0.9)),
    ],
)
def test_invalid_track_identity_is_rejected(candidates):
    request = SequenceRequest(candidates=candidates, limit=1)
    with pytest.raises(ValueError):
        sequence_playlist(request)


@pytest.mark.parametrize(
    "field_value",
    [math.nan, math.inf, -math.inf],
)
def test_non_finite_base_score_is_rejected(field_value):
    request = SequenceRequest(candidates=(candidate("a", field_value),), limit=1)
    with pytest.raises(ValueError):
        sequence_playlist(request)


def test_limit_and_deterministic_tie_breaking():
    request = SequenceRequest(
        candidates=(
            candidate("b", 0.8),
            candidate("a", 0.8),
            candidate("c", 0.7),
        ),
        limit=2,
    )
    first = sequence_playlist(request)
    second = sequence_playlist(request)
    assert first == second
    assert [item.track_id for item in first] == ["a", "b"]


@pytest.mark.parametrize(
    "mode",
    [SequenceMode.SMOOTH, SequenceMode.CONTRAST, SequenceMode.JOURNEY, SequenceMode.DISCOVERY],
)
def test_no_duplicates_and_limit(mode):
    candidates = tuple(candidate(str(i), 1.0 - i / 10) for i in range(5))
    result = sequence_playlist(
        SequenceRequest(candidates=candidates, mode=mode, limit=3)
    )
    assert len(result) == 3
    assert len({item.track_id for item in result}) == 3


def test_inputs_are_not_mutated():
    candidates = (
        candidate("a", 0.9),
        candidate("b", 0.8),
    )
    original = tuple(candidates)
    sequence_playlist(SequenceRequest(candidates=candidates, limit=2))
    assert candidates == original


@pytest.mark.parametrize("limit", [True, False, 0, -1, "2", 2.0, None])
def test_invalid_limits_are_rejected(limit):
    with pytest.raises(ValueError, match="limit must be a positive integer"):
        sequence_playlist(SequenceRequest(candidates=(candidate("a", 1.0),), limit=limit))


@pytest.mark.parametrize("energy", [-0.1, 1.1, math.nan, math.inf])
def test_invalid_energy_is_rejected(energy):
    with pytest.raises(ValueError, match="energy"):
        sequence_playlist(SequenceRequest(candidates=(candidate("a", 1.0, energy=energy),)))


@pytest.mark.parametrize("tempo", [0.0, -120.0, math.nan, math.inf])
def test_invalid_tempo_is_rejected(tempo):
    with pytest.raises(ValueError, match="tempo_bpm"):
        sequence_playlist(SequenceRequest(candidates=(candidate("a", 1.0, tempo_bpm=tempo),)))


@pytest.mark.parametrize("brightness", [-0.1, 1.1, math.nan])
def test_invalid_brightness_is_rejected(brightness):
    with pytest.raises(ValueError, match="brightness"):
        sequence_playlist(SequenceRequest(candidates=(candidate("a", 1.0, brightness=brightness),)))


@pytest.mark.parametrize("novelty", [math.nan, math.inf])
def test_non_finite_novelty_is_rejected(novelty):
    with pytest.raises(ValueError, match="novelty_score"):
        sequence_playlist(SequenceRequest(candidates=(candidate("a", 1.0, novelty=novelty),)))


def test_missing_optional_features_remain_valid():
    result = sequence_playlist(
        SequenceRequest(
            candidates=(
                candidate("b", 0.8, energy=None, tempo_bpm=None, brightness=None),
                candidate("a", 0.9, energy=None, tempo_bpm=None, brightness=None),
            ),
            mode=SequenceMode.SMOOTH,
            limit=2,
        )
    )
    assert [item.track_id for item in result] == ["a", "b"]


@pytest.mark.parametrize("mode", ["smooth", None, 123])
def test_unknown_mode_is_rejected(mode):
    with pytest.raises(ValueError, match="unknown sequence mode"):
        sequence_playlist(SequenceRequest(candidates=(candidate("a", 1.0),), mode=mode))


def test_empty_candidates_returns_empty():
    assert sequence_playlist(SequenceRequest(candidates=())) == ()
