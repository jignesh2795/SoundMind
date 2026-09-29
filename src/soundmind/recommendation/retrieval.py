from dataclasses import dataclass

from soundmind.recommendation.fusion import FusionWeights, rank_candidates


@dataclass(frozen=True)
class RetrievalQuery:
    text: str | None = None
    seed_track_id: str | None = None
    limit: int = 10

class RetrievalFusion:
    def __init__(self, weights=None):
        self.weights = weights or FusionWeights()
    def rank(self, candidates, *, limit=10):
        return rank_candidates(candidates, weights=self.weights, limit=limit)
