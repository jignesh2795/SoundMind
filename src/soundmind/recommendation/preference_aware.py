from dataclasses import replace
from datetime import datetime
from soundmind.preferences.models import ListeningEvent
from soundmind.preferences.scorer import PreferenceScorer
from soundmind.recommendation.fusion import CandidateSignals, FusionWeights, RankedCandidate, rank_candidates

class PreferenceAwareRecommender:
    """Apply listening-history preference evidence before fusion ranking."""
    def __init__(self, *, weights: FusionWeights | None = None, half_life_days: float = 30.0):
        self.weights = weights or FusionWeights()
        self.scorer = PreferenceScorer(half_life_days=half_life_days)

    def rank(self, candidates: list[CandidateSignals], events: list[ListeningEvent], *, now: datetime, limit=10) -> list[RankedCandidate]:
        preference = self.scorer.score_events(events, now=now)
        enriched = [replace(candidate, preference_score=preference.get(candidate.track_id, 0.0)) for candidate in candidates]
        return rank_candidates(enriched, weights=self.weights, limit=limit)
