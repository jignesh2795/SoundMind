from collections.abc import Iterable
from dataclasses import dataclass

from soundmind.intent import MusicIntent
from soundmind.recommendation.fusion import (
    CandidateSignals,
    FusionWeights,
    RankedCandidate,
    rank_candidates,
)


_MATCH_FIELDS = (
    "genres",
    "moods",
    "languages",
    "regions",
    "instrumentation",
    "music_types",
    "scenes",
)


@dataclass(frozen=True)
class IntentCandidate:
    track_id: str
    genres: tuple[str, ...] = ()
    moods: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    energy: float | None = None
    instrumentation: tuple[str, ...] = ()
    music_types: tuple[str, ...] = ()
    scenes: tuple[str, ...] = ()
    vocal_preference: str = "any"
    novelty_score: float = 0.0
    base_signals: CandidateSignals | None = None

    def __post_init__(self) -> None:
        if not self.track_id:
            raise ValueError("track_id must be non-empty")
        if self.energy is not None and not 0.0 <= self.energy <= 1.0:
            raise ValueError("energy must be within 0..1")
        if not 0.0 <= self.novelty_score <= 1.0:
            raise ValueError("novelty_score must be within 0..1")
        if self.vocal_preference not in ("any", "instrumental", "vocal"):
            raise ValueError(f"invalid vocal_preference: {self.vocal_preference!r}")


@dataclass(frozen=True)
class IntentMatch:
    intent_score: float
    energy_score: float = 0.0
    vocal_score: float = 0.0
    novelty_score: float = 0.0
    matched_dimensions: tuple[str, ...] = ()


def _overlap_score(requested: tuple[str, ...], available: tuple[str, ...]) -> float:
    if not requested:
        return 0.0
    return len(set(requested) & set(available)) / len(set(requested))


def _energy_score(intent_energy: float | None, candidate_energy: float | None) -> float:
    if intent_energy is None:
        return 0.0
    if candidate_energy is None:
        return 0.5
    return max(0.0, 1.0 - abs(intent_energy - candidate_energy))


def _vocal_score(intent: MusicIntent, candidate: IntentCandidate) -> float:
    if intent.vocal_preference == "any":
        return 0.0
    if "vocals" in intent.negative_terms:
        if candidate.vocal_preference == "vocal":
            return 0.0
        if candidate.vocal_preference == "instrumental":
            return 1.0
        return 0.5
    if candidate.vocal_preference == intent.vocal_preference:
        return 1.0
    if candidate.vocal_preference == "any":
        return 0.5
    return 0.0


def _novelty_score(intent: MusicIntent, candidate: IntentCandidate) -> float:
    if intent.novelty == "discovery":
        return candidate.novelty_score
    if intent.novelty == "familiar":
        return 1.0 - candidate.novelty_score
    return 0.0


class IntentRetrievalEngine:
    """Map M3 intent into deterministic signals consumed by M1 fusion."""

    def score(self, intent: MusicIntent, candidate: IntentCandidate) -> IntentMatch:
        scores: list[tuple[str, float]] = []

        for field in _MATCH_FIELDS:
            requested = getattr(intent, field)
            if requested:
                available = getattr(candidate, field)
                scores.append((field, _overlap_score(requested, available)))

        if intent.energy is not None:
            scores.append(("energy", _energy_score(intent.energy, candidate.energy)))

        if intent.vocal_preference != "any":
            scores.append(("vocal_preference", _vocal_score(intent, candidate)))

        if intent.novelty != "any":
            scores.append(("novelty", _novelty_score(intent, candidate)))

        if not scores:
            return IntentMatch(intent_score=0.0)

        intent_score = sum(score for _, score in scores) / len(scores)
        return IntentMatch(
            intent_score=intent_score,
            energy_score=_energy_score(intent.energy, candidate.energy),
            vocal_score=_vocal_score(intent, candidate),
            novelty_score=_novelty_score(intent, candidate),
            matched_dimensions=tuple(name for name, _ in scores),
        )

    def enrich(self, intent: MusicIntent, candidate: IntentCandidate) -> CandidateSignals:
        match = self.score(intent, candidate)
        base = candidate.base_signals or CandidateSignals(candidate.track_id)

        has_intent_constraints = bool(match.matched_dimensions)
        return CandidateSignals(
            track_id=candidate.track_id,
            metadata_score=match.intent_score if has_intent_constraints else base.metadata_score,
            dsp_score=(
                match.energy_score
                if intent.energy is not None
                else base.dsp_score
            ),
            learned_score=base.learned_score,
            preference_score=base.preference_score,
            novelty_score=(
                match.novelty_score
                if intent.novelty != "any"
                else base.novelty_score
            ),
            diversity_score=base.diversity_score,
        )

    def enrich_many(
        self,
        intent: MusicIntent,
        candidates: Iterable[IntentCandidate],
    ) -> list[CandidateSignals]:
        return [self.enrich(intent, candidate) for candidate in candidates]

    def rank(
        self,
        intent: MusicIntent,
        candidates: Iterable[IntentCandidate],
        *,
        weights: FusionWeights | None = None,
        limit: int = 10,
    ) -> list[RankedCandidate]:
        return rank_candidates(
            self.enrich_many(intent, candidates),
            weights=weights,
            limit=limit,
        )
