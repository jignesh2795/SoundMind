from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import math
from typing import ClassVar
from soundmind.preferences.models import ListeningEvent, ListeningEventType

@dataclass(frozen=True)
class PreferenceEvidence:
    track_id: str
    positive: float = 0.0
    negative: float = 0.0
    replay: float = 0.0
    skip: float = 0.0

    @property
    def net(self) -> float:
        return self.positive + self.replay - self.negative - self.skip

class PreferenceScorer:
    """Convert listening events into a bounded track-level preference signal."""
    WEIGHTS = {
        ListeningEventType.PLAY: (0.15, 0.0, 0.0, 0.0),
        ListeningEventType.COMPLETE: (0.35, 0.0, 0.0, 0.0),
        ListeningEventType.LIKE: (1.0, 0.0, 0.0, 0.0),
        ListeningEventType.DISLIKE: (0.0, 1.0, 0.0, 0.0),
        ListeningEventType.REPLAY: (0.0, 0.0, 1.25, 0.0),
        ListeningEventType.SKIP: (0.0, 0.0, 0.0, 0.75),
    }

    def __init__(self, *, half_life_days: float = 30.0):
        if half_life_days <= 0:
            raise ValueError("half_life_days must be positive")
        self.half_life_days = half_life_days

    def score_events(self, events: list[ListeningEvent], *, now: datetime) -> dict[str, float]:
        evidence: dict[str, PreferenceEvidence] = defaultdict(lambda: PreferenceEvidence(""))
        for event in events:
            if event.occurred_at.tzinfo is None or now.tzinfo is None:
                raise ValueError("event and now must be timezone-aware")
            age_days = max(0.0, (now - event.occurred_at).total_seconds() / 86400.0)
            decay = 0.5 ** (age_days / self.half_life_days)
            p, n, r, s = self.WEIGHTS[event.event_type]
            current = evidence[event.track_id]
            evidence[event.track_id] = PreferenceEvidence(
                event.track_id,
                current.positive + p * decay,
                current.negative + n * decay,
                current.replay + r * decay,
                current.skip + s * decay,
            )
        return {track_id: self._bounded(signal.net) for track_id, signal in evidence.items()}

    @staticmethod
    def _bounded(value: float) -> float:
        if not math.isfinite(value):
            return 0.0
        return math.tanh(value / 2.0)
