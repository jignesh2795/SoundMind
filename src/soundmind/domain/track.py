from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    LOCAL_FILE = "local_file"

class TrackStatus(str, Enum):
    ACTIVE = "active"
    MISSING = "missing"

@dataclass(frozen=True)
class Track:
    track_id: str
    content_hash: str
    source_type: SourceType
    source_uri: str
    file_name: str
    file_size: int
    modified_at_ns: int
    status: TrackStatus
    created_at: datetime
    updated_at: datetime
