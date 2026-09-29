"""Context-specific novelty scoring from existing listening exposure."""

import math
from dataclasses import dataclass
from datetime import datetime

from soundmind.preferences.models import ListeningEvent


@dataclass(frozen=True)
class ContextualNoveltyScorer:
    """Derive bounded novelty from recency-weighted contextual exposure."""

    half_life_days: float = 30.0

    def __post_init__(self) -> None:
        if self.half_life_days <= 0:
            raise ValueError("half_life_days must be positive")

    def score_events(
        self,
        events: list[ListeningEvent],
        *,
        context: str | None,
        now: datetime,
    ) -> dict[str, float]:
        """Return novelty scores for tracks with matching contextual exposure."""
        if context is None or not context.strip():
            return {}
        if now.tzinfo is None:
            raise ValueError("event and now must be timezone-aware")

        normalized = context.strip().lower()
        exposure: dict[str, float] = {}

        for event in events:
            if event.occurred_at.tzinfo is None:
                raise ValueError("event and now must be timezone-aware")
            event_context = event.context
            if event_context is None or event_context.strip().lower() != normalized:
                continue

            age_days = max(
                0.0,
                (now - event.occurred_at).total_seconds() / 86400.0,
            )
            decay = 0.5 ** (age_days / self.half_life_days)
            exposure[event.track_id] = exposure.get(event.track_id, 0.0) + decay

        scores = {
            track_id: 1.0 / (1.0 + value)
            for track_id, value in exposure.items()
            if math.isfinite(value)
        }
        return scores
