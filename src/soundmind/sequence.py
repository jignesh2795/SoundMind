"""M2 deterministic playlist sequencing engine (see docs/m2-sequence-contract.md)."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class SequenceMode(str, Enum):
    SMOOTH = "smooth"
    CONTRAST = "contrast"
    JOURNEY = "journey"
    DISCOVERY = "discovery"


@dataclass(frozen=True)
class SequenceCandidate:
    track_id: str
    base_score: float
    energy: float | None = None
    tempo_bpm: float | None = None
    brightness: float | None = None
    novelty_score: float = 0.0


@dataclass(frozen=True)
class SequenceRequest:
    candidates: tuple[SequenceCandidate, ...] | list[SequenceCandidate]
    mode: SequenceMode = SequenceMode.SMOOTH
    seed_track_id: str | None = None
    limit: int = 10


@dataclass(frozen=True)
class SequenceItem:
    track_id: str
    sequence_score: float
    base_score: float


# Named transition weights (inspectable, deterministic).
ENERGY_WEIGHT = 0.5
TEMPO_WEIGHT = 0.3
TEMPO_NORM_BPM = 60.0
BRIGHTNESS_WEIGHT = 0.2
BASE_WEIGHT = 1.0
TRANSITION_WEIGHT = 1.0
NOVELTY_WEIGHT = 0.5
JOURNEY_TARGET_WEIGHT = 1.0


def journey_target_energy(position: int, total: int) -> float:
    """Explicit energy arc: start moderate (0.3), build to high (0.9)."""
    if total <= 1:
        return 0.5
    fraction = position / (total - 1)
    return round(0.3 + 0.6 * fraction, 10)


def transition_distance(a: SequenceCandidate, b: SequenceCandidate) -> float:
    energy_term = (
        abs(a.energy - b.energy) * ENERGY_WEIGHT
        if a.energy is not None and b.energy is not None
        else 0.0
    )
    tempo_term = (
        abs(a.tempo_bpm - b.tempo_bpm) / TEMPO_NORM_BPM * TEMPO_WEIGHT
        if a.tempo_bpm is not None and b.tempo_bpm is not None
        else 0.0
    )
    brightness_term = (
        abs(a.brightness - b.brightness) * BRIGHTNESS_WEIGHT
        if a.brightness is not None and b.brightness is not None
        else 0.0
    )
    return energy_term + tempo_term + brightness_term


def _finite(value: float, *, name: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _validate_candidate(candidate: SequenceCandidate) -> None:
    if not candidate.track_id:
        raise ValueError("track_id must be non-empty")
    _finite(candidate.base_score, name="base_score")
    if candidate.energy is not None:
        _finite(candidate.energy, name="energy")
        if not 0.0 <= candidate.energy <= 1.0:
            raise ValueError("energy must be within 0..1")
    if candidate.tempo_bpm is not None:
        _finite(candidate.tempo_bpm, name="tempo_bpm")
        if candidate.tempo_bpm <= 0:
            raise ValueError("tempo_bpm must be positive")
    if candidate.brightness is not None:
        _finite(candidate.brightness, name="brightness")
        if not 0.0 <= candidate.brightness <= 1.0:
            raise ValueError("brightness must be within 0..1")
    _finite(candidate.novelty_score, name="novelty_score")


def _step_score(
    candidate: SequenceCandidate,
    current: SequenceCandidate,
    *,
    mode: SequenceMode,
    position: int,
    total: int,
) -> float:
    base = float(candidate.base_score)
    distance = transition_distance(current, candidate)
    if mode is SequenceMode.SMOOTH:
        return BASE_WEIGHT * base - TRANSITION_WEIGHT * distance
    if mode is SequenceMode.CONTRAST:
        return BASE_WEIGHT * base + TRANSITION_WEIGHT * distance
    if mode is SequenceMode.JOURNEY:
        target = journey_target_energy(position, total)
        if candidate.energy is None:
            target_term = 0.0
        else:
            target_term = abs(candidate.energy - target)
        return BASE_WEIGHT * base - JOURNEY_TARGET_WEIGHT * target_term
    # DISCOVERY: relevance plus supplied novelty (absent novelty contributes zero).
    return BASE_WEIGHT * base + NOVELTY_WEIGHT * float(candidate.novelty_score)


def sequence_playlist(request: SequenceRequest) -> tuple[SequenceItem, ...]:
    candidates: Sequence[SequenceCandidate] = request.candidates
    mode = request.mode
    if not isinstance(mode, SequenceMode):
        raise ValueError(f"unknown sequence mode: {mode!r}")  # noqa: TRY004
    limit = request.limit
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    seen: set[str] = set()
    for candidate_item in candidates:
        _validate_candidate(candidate_item)
        if candidate_item.track_id in seen:
            raise ValueError(f"duplicate track_id: {candidate_item.track_id!r}")
        seen.add(candidate_item.track_id)

    pool = list(candidates)
    if not pool:
        return ()

    first: SequenceCandidate
    if request.seed_track_id is not None:
        matches = [c for c in pool if c.track_id == request.seed_track_id]
        if not matches:
            raise ValueError(f"seed_track_id not found: {request.seed_track_id!r}")
        first = matches[0]
    else:
        first = min(pool, key=lambda c: (-c.base_score, c.track_id))

    total = min(limit, len(pool))
    ordered: list[SequenceCandidate] = [first]
    remaining = [c for c in pool if c.track_id != first.track_id]
    while len(ordered) < total:
        current = ordered[-1]
        position = len(ordered)
        best = min(
            remaining,
            key=lambda c: (
                -_step_score(c, current, mode=mode, position=position, total=total),
                c.track_id,
            ),
        )
        ordered.append(best)
        remaining = [c for c in remaining if c.track_id != best.track_id]

    items: list[SequenceItem] = []
    current_item: SequenceCandidate | None = None
    for index, candidate_item in enumerate(ordered):
        if index == 0:
            score = float(candidate_item.base_score)
        else:
            assert current_item is not None
            score = _step_score(
                candidate_item,
                current_item,
                mode=mode,
                position=index,
                total=total,
            )
        items.append(
            SequenceItem(
                track_id=candidate_item.track_id,
                sequence_score=score,
                base_score=float(candidate_item.base_score),
            )
        )
        current_item = candidate_item
    return tuple(items)
