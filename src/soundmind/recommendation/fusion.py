from dataclasses import dataclass
import math
from typing import Iterable

@dataclass(frozen=True)
class CandidateSignals:
    track_id: str
    metadata_score: float = 0.0
    dsp_score: float = 0.0
    learned_score: float = 0.0
    novelty_score: float = 0.0
    diversity_score: float = 0.0

@dataclass(frozen=True)
class FusionWeights:
    metadata: float = .20
    dsp: float = .20
    learned: float = .40
    novelty: float = .10
    diversity: float = .10
    def normalized(self):
        total = sum(vars(self).values())
        if total <= 0: raise ValueError("At least one fusion weight must be positive")
        return FusionWeights(*(getattr(self, k)/total for k in vars(self)))

@dataclass(frozen=True)
class RankedCandidate:
    track_id: str
    score: float
    signals: CandidateSignals

def fuse_score(candidate, weights):
    w = weights.normalized()
    f = lambda x: x if math.isfinite(x) else 0.0
    return (f(candidate.metadata_score)*w.metadata + f(candidate.dsp_score)*w.dsp +
            f(candidate.learned_score)*w.learned + f(candidate.novelty_score)*w.novelty +
            f(candidate.diversity_score)*w.diversity)

def rank_candidates(candidates: Iterable[CandidateSignals], *, weights=None, limit=10):
    if limit <= 0: raise ValueError("limit must be positive")
    weights = weights or FusionWeights()
    ranked = [RankedCandidate(c.track_id, fuse_score(c, weights), c) for c in candidates]
    ranked.sort(key=lambda x: (-x.score, x.track_id))
    return ranked[:limit]
