from dataclasses import dataclass


@dataclass(frozen=True)
class SignalContribution:
    name: str
    raw_score: float
    weight: float
    contribution: float

@dataclass(frozen=True)
class RecommendationExplanation:
    track_id: str
    total_score: float
    contributions: tuple[SignalContribution, ...]

    @property
    def strongest_signal(self) -> str | None:
        if not self.contributions:
            return None
        return max(self.contributions, key=lambda item: abs(item.contribution)).name
