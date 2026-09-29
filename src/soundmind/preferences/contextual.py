"""Context-aware preference scoring from existing listening events."""

from dataclasses import dataclass
from datetime import datetime

from soundmind.preferences.models import ListeningEvent
from soundmind.preferences.scorer import PreferenceScorer


@dataclass(frozen=True)
class ContextualPreferenceScorer:
    """Score listening events for one normalized context."""

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
        """Return bounded preference scores from events matching context."""
        if context is None or not context.strip():
            return {}
        if now.tzinfo is None:
            raise ValueError("event and now must be timezone-aware")

        normalized = context.strip().lower()
        matching = [
            event
            for event in events
            if event.context is not None
            and event.context.strip().lower() == normalized
        ]
        return PreferenceScorer(half_life_days=self.half_life_days).score_events(
            matching,
            now=now,
        )
