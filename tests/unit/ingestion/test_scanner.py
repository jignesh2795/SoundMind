from pathlib import Path
from soundmind.ingestion.scanner import SUPPORTED_EXTENSIONS, file_uri, scan_directory
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow

def test_file_uri_and_extensions(tmp_path: Path):
    assert file_uri(tmp_path / "a.mp3").startswith("file://")
    assert ".mp3" in SUPPORTED_EXTENSIONS

def test_scan_creates_track_and_marks_missing(tmp_path: Path):
    music = tmp_path / "music"
    music.mkdir()
    track = music / "song.mp3"
    track.write_bytes(b"sample")
    sf = create_session_factory(tmp_path / "db.sqlite")
    with sf() as session:
        assert scan_directory(session, music) == 1
        row = session.query(TrackRow).one()
        assert row.status == "active"
        assert row.file_name == "song.mp3"
    track.unlink()
    with sf() as session:
        assert scan_directory(session, music) == 0
        row = session.query(TrackRow).one()
        assert row.status == "missing"
