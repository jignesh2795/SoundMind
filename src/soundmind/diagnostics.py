from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingIssue:
    stage: str
    source: str
    error_type: str
    message: str
