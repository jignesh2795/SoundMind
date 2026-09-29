from dataclasses import dataclass
from pathlib import Path

from soundmind.diagnostics import ProcessingIssue


@dataclass(frozen=True)
class AudioMetadata:
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    composer: str | None = None
    genre: str | None = None
    year: int | None = None
    duration_seconds: float | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    channels: int | None = None


def _first(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else None
    return str(value)


def extract_metadata(
    path: Path, *, diagnostics: list[ProcessingIssue] | None = None
) -> AudioMetadata:
    try:
        from mutagen import File

        audio = File(path, easy=True)
        if audio is None:
            return AudioMetadata()
        info = audio.info
        year_value = _first(audio.get("date") or audio.get("year"))
        try:
            year = int(year_value[:4]) if year_value else None
        except (TypeError, ValueError):
            year = None
        return AudioMetadata(
            title=_first(audio.get("title")),
            artist=_first(audio.get("artist")),
            album=_first(audio.get("album")),
            album_artist=_first(audio.get("albumartist")),
            composer=_first(audio.get("composer")),
            genre=_first(audio.get("genre")),
            year=year,
            duration_seconds=float(getattr(info, "length", 0.0) or 0.0) or None,
            bitrate=int(getattr(info, "bitrate", 0) or 0) or None,
            sample_rate=int(getattr(info, "sample_rate", 0) or 0) or None,
            channels=int(getattr(info, "channels", 0) or 0) or None,
        )
    except Exception as exc:  # noqa: BLE001
        if diagnostics is not None:
            diagnostics.append(
                ProcessingIssue("metadata", str(path), type(exc).__name__, str(exc))
            )
        return AudioMetadata()
