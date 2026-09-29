from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisConfig:
    max_analysis_seconds: float = 180.0
    analysis_offset_seconds: float = 0.0

    def __post_init__(self):
        if self.max_analysis_seconds <= 0:
            raise ValueError("max_analysis_seconds must be positive")
        if self.analysis_offset_seconds < 0:
            raise ValueError("analysis_offset_seconds must be non-negative")

    @property
    def analysis_version(self) -> str:
        return (
            f"m0.5|max={self.max_analysis_seconds:g}"
            f"|off={self.analysis_offset_seconds:g}"
        )
