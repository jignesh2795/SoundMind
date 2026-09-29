"""Learned audio similarity enrichment for recommendation candidates."""

import math
from collections.abc import Iterable
from dataclasses import replace
from typing import Protocol

from soundmind.recommendation.fusion import CandidateSignals
from soundmind.recommendation.intent_retrieval import IntentCandidate
from soundmind.vector.index import SimilarityResult


class LearnedSimilarityProvider(Protocol):
    """Provide learned audio similarity for a seed track."""

    def similar(self, track_id: str, *, limit: int = 10) -> list[SimilarityResult]:
        """Return deterministic learned similarities for a seed track."""


def _similarity_score(raw_score: float) -> float:
    """Map cosine similarity from [-1, 1] into the fusion score range [0, 1]."""
    if not math.isfinite(raw_score):
        return 0.0
    return max(0.0, min(1.0, (raw_score + 1.0) / 2.0))


class LearnedRetrievalEngine:
    """Enrich candidate signals with existing learned audio similarity."""

    def __init__(self, provider: LearnedSimilarityProvider) -> None:
        self._provider = provider

    def enrich(
        self,
        seed_track_id: str,
        candidates: Iterable[IntentCandidate],
        *,
        limit: int | None = None,
    ) -> tuple[IntentCandidate, ...]:
        """Attach learned similarity to candidates without changing other signals."""
        if not seed_track_id:
            raise ValueError("seed_track_id must be non-empty")

        materialized = tuple(candidates)
        seen: set[str] = set()
        for candidate in materialized:
            if candidate.track_id in seen:
                raise ValueError(f"duplicate track_id: {candidate.track_id!r}")
            seen.add(candidate.track_id)

        if not materialized:
            return ()
        effective_limit = limit if limit is not None else len(materialized)
        if effective_limit <= 0:
            raise ValueError("limit must be positive")

        similarities = self._provider.similar(
            seed_track_id,
            limit=max(effective_limit, len(materialized)),
        )
        scores = {
            result.track_id: _similarity_score(result.score)
            for result in similarities
            if result.track_id in seen and result.track_id != seed_track_id
        }

        enriched: list[IntentCandidate] = []
        for candidate in materialized:
            base = candidate.base_signals
            if base is None:
                base = CandidateSignals(candidate.track_id)
            learned_score = scores.get(candidate.track_id, base.learned_score)
            enriched.append(
                replace(
                    candidate,
                    base_signals=replace(base, learned_score=learned_score),
                )
            )
        return tuple(enriched)
