import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from soundmind.analysis.dsp import analyze_audio
from soundmind.config import AnalysisConfig
from soundmind.diagnostics import ProcessingIssue
from soundmind.ingestion.fingerprint import sha256_file, stable_track_id
from soundmind.ingestion.metadata import extract_metadata
from soundmind.storage.models import ScanStateRow, TrackRow

SUPPORTED_EXTENSIONS = frozenset({".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".aac"})


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def scan_directory(
    session,
    root: Path,
    *,
    compute_content_hash: bool = True,
    analysis_config: AnalysisConfig | None = None,
    analyze: bool = True,
    diagnostics: list[ProcessingIssue] | None = None,
) -> int:
    root = root.expanduser().resolve()
    analysis_config = analysis_config or AnalysisConfig()
    if not root.is_dir():
        raise NotADirectoryError(root)
    now = datetime.now(UTC)
    seen: set[str] = set()
    count = 0
    for path in sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ):
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
            and (not analyze or existing.analysis_version == "m0.5")
            and (not analyze or existing.analysis_seconds is not None)
        )
        if unchanged:
            state.last_seen_at = now
            existing.updated_at = now
            existing.status = "active"
            continue

        content_hash = (
            sha256_file(path) if compute_content_hash else (existing.content_hash if existing else "")
        )
        if not content_hash:
            content_hash = sha256_file(path)
        metadata = extract_metadata(path, diagnostics=diagnostics)
        track_id = stable_track_id(uri)
        if existing is None:
            existing = TrackRow(
                track_id=track_id,
                content_hash=content_hash,
                source_type="local_file",
                source_uri=uri,
                file_name=path.name,
                file_size=stat.st_size,
                modified_at_ns=stat.st_mtime_ns,
                status="active",
                created_at=now,
                updated_at=now,
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

        if analyze:
            try:
                analysis = analyze_audio(
                    path,
                    max_analysis_seconds=analysis_config.max_analysis_seconds,
                    analysis_offset_seconds=analysis_config.analysis_offset_seconds,
                )
            except Exception as exc:  # noqa: BLE001
                if diagnostics is not None:
                    diagnostics.append(
                        ProcessingIssue("analysis", str(path), type(exc).__name__, str(exc))
                    )
                analysis = None

            if analysis is None:
                existing.analysis_mode = "failed"
                existing.analysis_seconds = None
                existing.analysis_version = "m0.5"
            else:
                existing.sample_rate = analysis.sample_rate
                existing.channels = analysis.channels
                existing.tempo_bpm = analysis.tempo_bpm
                existing.rms_energy = analysis.rms_energy
                existing.spectral_centroid = analysis.spectral_centroid
                existing.spectral_bandwidth = analysis.spectral_bandwidth
                existing.spectral_rolloff = analysis.spectral_rolloff
                existing.zero_crossing_rate = analysis.zero_crossing_rate
                existing.mfcc_json = json.dumps(analysis.mfcc)
                existing.chroma_json = json.dumps(analysis.chroma)
                existing.analysis_mode = analysis.analysis_mode
                existing.analysis_seconds = analysis.analyzed_seconds
                existing.analysis_version = "m0.5"

        if state is None:
            state = ScanStateRow(
                source_uri=uri,
                last_seen_at=now,
                file_size=stat.st_size,
                modified_at_ns=stat.st_mtime_ns,
                content_hash=content_hash,
            )
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
