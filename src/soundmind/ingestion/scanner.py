from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from sqlalchemy import select
from soundmind.ingestion.fingerprint import sha256_file, stable_track_id
from soundmind.ingestion.metadata import extract_metadata
from soundmind.storage.models import ScanStateRow, TrackRow

SUPPORTED_EXTENSIONS = frozenset({".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".aac"})

def file_uri(path: Path) -> str:
    return path.resolve().as_uri()

def scan_directory(session, root: Path, *, compute_content_hash: bool = True) -> int:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    now = datetime.now(timezone.utc)
    seen: set[str] = set()
    count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS):
        uri = file_uri(path)
        seen.add(uri)
        stat = path.stat()
        existing = session.get(TrackRow, stable_track_id(uri))
        state = session.get(ScanStateRow, uri)
        unchanged = (
            state is not None
            and state.file_size == stat.st_size
            and state.modified_at_ns == stat.st_mtime_ns
            and existing is not None
        )
        if unchanged:
            state.last_seen_at = now
            existing.updated_at = now
            existing.status = "active"
            continue
        content_hash = sha256_file(path) if compute_content_hash else (existing.content_hash if existing else "")
        if not content_hash:
            content_hash = sha256_file(path)
        metadata = extract_metadata(path)
        track_id = stable_track_id(uri)
        if existing is None:
            existing = TrackRow(
                track_id=track_id, content_hash=content_hash, source_type="local_file",
                source_uri=uri, file_name=path.name, file_size=stat.st_size,
                modified_at_ns=stat.st_mtime_ns, status="active", created_at=now, updated_at=now,
            )
            session.add(existing)
        else:
            existing.content_hash = content_hash
            existing.file_name = path.name
            existing.file_size = stat.st_size
            existing.modified_at_ns = stat.st_mtime_ns
            existing.status = "active"
            existing.updated_at = now
        for key, value in metadata.__dict__.items():
            setattr(existing, key, value)
        if state is None:
            state = ScanStateRow(source_uri=uri, last_seen_at=now, file_size=stat.st_size, modified_at_ns=stat.st_mtime_ns, content_hash=content_hash)
            session.add(state)
        else:
            state.last_seen_at = now
            state.file_size = stat.st_size
            state.modified_at_ns = stat.st_mtime_ns
            state.content_hash = content_hash
        count += 1
    for row in session.scalars(select(TrackRow).where(TrackRow.status == "active")).all():
        if row.source_uri.startswith("file://") and row.source_uri not in seen:
            row.status = "missing"
            row.updated_at = now
    session.commit()
    return count
