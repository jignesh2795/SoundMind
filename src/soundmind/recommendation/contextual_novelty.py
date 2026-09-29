"""Contextual novelty integration with the existing M1 ranking boundary."""

from dataclasses import replace
from datetime import datetime

from soundmind.preferences.models import ListeningEvent
from soundmind.preferences.novelty import ContextualNoveltyScorer
from soundmind.recommendation.fusion import (
    CandidateSignals,
    FusionWeights,
    RankedCandidate,
    rank_candidates,
)


class ContextualNoveltyRecommender:
    """Apply contextual novelty to M1 fusion without changing other signals."""

    def __init__(
        self,
        *,
        weights: FusionWeights | None = None,
        half_life_days: float = 30.0,
    ) -> None:
        self.weights = weights or FusionWeights()
        self.scorer = ContextualNoveltyScorer(half_life_days=half_life_days)

    def rank(
        self,
        candidates: list[CandidateSignals],
        events: list[ListeningEvent],
        *,
        context: str,
        now: datetime,
        limit: int = 10,
    ) -> list[RankedCandidate]:
        if not context.strip():
            raise ValueError("context must be non-empty")

        novelty = self.scorer.score_events(
            events,
            context=context,
            now=now,
        )
        enriched = [
            replace(
                candidate,
                novelty_score=novelty.get(candidate.track_id, 1.0),
            )
            for candidate in candidates
        ]
        return rank_candidates(enriched, weights=self.weights, limit=limit)
