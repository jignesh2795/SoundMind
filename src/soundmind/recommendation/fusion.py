import math
from collections.abc import Iterable
from dataclasses import dataclass

from soundmind.recommendation.explanation import RecommendationExplanation, SignalContribution


@dataclass(frozen=True)
class CandidateSignals:
    track_id: str
    metadata_score: float = 0.0
    dsp_score: float = 0.0
    learned_score: float = 0.0
    preference_score: float = 0.0
    novelty_score: float = 0.0
    diversity_score: float = 0.0

@dataclass(frozen=True)
class FusionWeights:
    metadata: float = .18
    dsp: float = .18
    learned: float = .36
    preference: float = .18
    novelty: float = .05
    diversity: float = .05

    def normalized(self):
        values = (self.metadata, self.dsp, self.learned, self.preference, self.novelty, self.diversity)
        total = sum(values)
        if total <= 0:
            raise ValueError("At least one fusion weight must be positive")
        return FusionWeights(*(value / total for value in values))

@dataclass(frozen=True)
class RankedCandidate:
    track_id: str
    score: float
    signals: CandidateSignals
    explanation: RecommendationExplanation

def _finite(value: float) -> float:
    return value if math.isfinite(value) else 0.0

def explain_candidate(candidate: CandidateSignals, weights: FusionWeights) -> RecommendationExplanation:
    w = weights.normalized()
    pairs = (
        ("metadata", candidate.metadata_score, w.metadata),
        ("dsp", candidate.dsp_score, w.dsp),
        ("learned", candidate.learned_score, w.learned),
        ("preference", candidate.preference_score, w.preference),
        ("novelty", candidate.novelty_score, w.novelty),
        ("diversity", candidate.diversity_score, w.diversity),
    )
    contributions = tuple(
        SignalContribution(name, _finite(raw), weight, _finite(raw) * weight)
        for name, raw, weight in pairs
    )
    return RecommendationExplanation(candidate.track_id, sum(x.contribution for x in contributions), contributions)

def fuse_score(candidate: CandidateSignals, weights: FusionWeights) -> float:
    return explain_candidate(candidate, weights).total_score

def rank_candidates(candidates: Iterable[CandidateSignals], *, weights=None, limit=10):
    if limit <= 0:
        raise ValueError("limit must be positive")
    effective = weights or FusionWeights()
    ranked = [
        RankedCandidate(c.track_id, fuse_score(c, effective), c, explain_candidate(c, effective))
        for c in candidates
    ]
    ranked.sort(key=lambda x: (-x.score, x.track_id))
    return ranked[:limit]
