from pathlib import Path

from soundmind.analysis.dsp import AudioAnalysis
from soundmind.config import AnalysisConfig
from soundmind.ingestion import scanner as scanner_module
from soundmind.ingestion.metadata import AudioMetadata
from soundmind.ingestion.scanner import scan_directory
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


def _make_music(tmp_path: Path) -> Path:
    music = tmp_path / "music"
    music.mkdir()
    (music / "song.mp3").write_bytes(b"sample")
    return music


def _fake_analysis(analyzed_seconds: float = 60.0) -> AudioAnalysis:
    return AudioAnalysis(
        None,
        44100,
        2,
        120.0,
        0.1,
        1000.0,
        500.0,
        2000.0,
        0.05,
        (0.1, 0.2),
        (0.3, 0.4),
        analyzed_seconds,
        "bounded",
    )


def test_changing_max_seconds_forces_reanalysis(tmp_path: Path, monkeypatch):
    music = _make_music(tmp_path)
    calls: list[tuple[float, float]] = []

    def fake_analyze(path, *, max_analysis_seconds, analysis_offset_seconds):
        calls.append((max_analysis_seconds, analysis_offset_seconds))
        return _fake_analysis(min(max_analysis_seconds, 60.0))

    monkeypatch.setattr(scanner_module, "analyze_audio", fake_analyze)
    factory = create_session_factory(tmp_path / "db.sqlite")

    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(60.0, 0.0)) == 1
    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(60.0, 0.0)) == 0
    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(180.0, 0.0)) == 1
    assert calls[0] == (60.0, 0.0)
    assert calls[-1] == (180.0, 0.0)


def test_changing_offset_forces_reanalysis(tmp_path: Path, monkeypatch):
    music = _make_music(tmp_path)

    def fake_analyze(path, *, max_analysis_seconds, analysis_offset_seconds):
        return _fake_analysis(60.0)

    monkeypatch.setattr(scanner_module, "analyze_audio", fake_analyze)
    factory = create_session_factory(tmp_path / "db.sqlite")

    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(60.0, 0.0)) == 1
    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(60.0, 0.0)) == 0
    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(60.0, 120.0)) == 1


def test_true_duration_preserved_not_overwritten_by_window(tmp_path: Path, monkeypatch):
    music = _make_music(tmp_path)
    monkeypatch.setattr(
        scanner_module,
        "extract_metadata",
        lambda path, diagnostics=None: AudioMetadata(duration_seconds=300.0),
    )
    monkeypatch.setattr(
        scanner_module,
        "analyze_audio",
        lambda path, *, max_analysis_seconds, analysis_offset_seconds: _fake_analysis(60.0),
    )
    factory = create_session_factory(tmp_path / "db.sqlite")

    with factory() as session:
        assert scan_directory(session, music, analysis_config=AnalysisConfig(60.0, 0.0)) == 1
        row = session.query(TrackRow).one()
        assert row.duration_seconds == 300.0
        assert row.analysis_seconds == 60.0
