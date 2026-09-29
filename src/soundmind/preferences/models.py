from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ListeningEventType(str, Enum):
    PLAY="play"; COMPLETE="complete"; SKIP="skip"; LIKE="like"; DISLIKE="dislike"; REPLAY="replay"

@dataclass(frozen=True)
class ListeningEvent:
    track_id: str
    event_type: ListeningEventType
    occurred_at: datetime
    context: str | None = None
    seconds_played: float | None = None

@dataclass(frozen=True)
class TasteProfile:
    positive_track_ids: tuple[str,...]=()
    negative_track_ids: tuple[str,...]=()
    replay_track_ids: tuple[str,...]=()
    skipped_track_ids: tuple[str,...]=()
    contexts: tuple[str,...]=()
