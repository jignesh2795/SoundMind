from dataclasses import replace
from datetime import datetime

from soundmind.preferences.contextual import ContextualPreferenceScorer
from soundmind.preferences.models import ListeningEvent
from soundmind.preferences.scorer import PreferenceScorer
from soundmind.recommendation.fusion import (
    CandidateSignals,
    FusionWeights,
    RankedCandidate,
    rank_candidates,
)


class PreferenceAwareRecommender:
    """Apply global or contextual listening-history preference before fusion ranking."""

    def __init__(self, *, weights: FusionWeights | None = None, half_life_days: float = 30.0):
        self.weights = weights or FusionWeights()
        self.scorer = PreferenceScorer(half_life_days=half_life_days)
        self.contextual_scorer = ContextualPreferenceScorer(
            half_life_days=half_life_days
        )

    def rank(
        self,
        candidates: list[CandidateSignals],
        events: list[ListeningEvent],
        *,
        now: datetime,
        context: str | None = None,
        limit=10,
    ) -> list[RankedCandidate]:
        if context is None:
            preference = self.scorer.score_events(events, now=now)
        else:
            preference = self.contextual_scorer.score_events(
                events,
                context=context,
                now=now,
            )

        enriched = [
            replace(
                candidate,
                preference_score=preference.get(candidate.track_id, 0.0),
            )
            for candidate in candidates
        ]
        return rank_candidates(enriched, weights=self.weights, limit=limit)
