from pathlib import Path
from types import SimpleNamespace

import pytest

from soundmind.cli.main import build_parser, main


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _stub_session_factory(monkeypatch, captured):
    def factory(path):
        captured["db"] = path
        return lambda: _FakeSession()

    monkeypatch.setattr("soundmind.cli.main.create_session_factory", factory)


def test_scan_parser_captures_defaults() -> None:
    args = build_parser().parse_args(["scan", "music"])

    assert args.command == "scan"
    assert args.music_folder == Path("music")
    assert args.db == Path("data/database/soundmind.db")
    assert args.no_content_hash is False
    assert args.no_analysis is False
    assert args.analysis_seconds == 180.0
    assert args.analysis_offset == 0.0


def test_scan_forwards_options_and_renders_count(monkeypatch, capsys) -> None:
    captured = {}

    def fake_scan(session, root, **kwargs):
        captured["session"] = session
        captured["root"] = root
        captured["kwargs"] = kwargs
        return 7

    monkeypatch.setattr("soundmind.cli.main.scan_directory", fake_scan)
    _stub_session_factory(monkeypatch, captured)

    assert (
        main(
            [
                "scan",
                "music",
                "--db",
                "custom.db",
                "--no-content-hash",
                "--no-analysis",
                "--analysis-seconds",
                "30",
                "--analysis-offset",
                "5",
            ]
        )
        == 0
    )

    assert captured["db"] == Path("custom.db")
    assert captured["root"] == Path("music")
    assert isinstance(captured["session"], _FakeSession)
    assert captured["kwargs"]["compute_content_hash"] is False
    assert captured["kwargs"]["analyze"] is False
    assert captured["kwargs"]["analysis_config"].max_analysis_seconds == 30.0
    assert captured["kwargs"]["analysis_config"].analysis_offset_seconds == 5.0
    assert capsys.readouterr().out == "Scanned changed tracks: 7\n"


def test_scan_uses_default_analysis_behavior(monkeypatch, capsys) -> None:
    captured = {}

    def fake_scan(session, root, **kwargs):
        captured["kwargs"] = kwargs
        return 0

    monkeypatch.setattr("soundmind.cli.main.scan_directory", fake_scan)
    _stub_session_factory(monkeypatch, captured)

    assert main(["scan", "music"]) == 0

    assert captured["db"] == Path("data/database/soundmind.db")
    assert captured["kwargs"]["compute_content_hash"] is True
    assert captured["kwargs"]["analyze"] is True
    assert captured["kwargs"]["analysis_config"].max_analysis_seconds == 180.0
    assert captured["kwargs"]["analysis_config"].analysis_offset_seconds == 0.0
    assert capsys.readouterr().out == "Scanned changed tracks: 0\n"


def test_scan_requires_music_folder() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan"])

    assert exc_info.value.code == 2


def test_scan_rejects_non_numeric_analysis_seconds() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["scan", "music", "--analysis-seconds", "soon"])

    assert exc_info.value.code == 2


def test_fetch_effnet_parser_defaults() -> None:
    args = build_parser().parse_args(["model", "fetch-effnet"])

    assert args.command == "model"
    assert args.model_command == "fetch-effnet"
    assert args.path == Path("data/models/discogs-effnet-bsdynamic-1.onnx")


def test_fetch_effnet_prints_returned_path(monkeypatch, capsys) -> None:
    captured = {}

    def fake_fetch(path):
        captured["path"] = path
        return Path("custom/model.onnx")

    monkeypatch.setattr("soundmind.cli.main.fetch_effnet_model", fake_fetch)

    assert main(["model", "fetch-effnet", "--path", "custom/model.onnx"]) == 0

    assert captured["path"] == Path("custom/model.onnx")
    assert capsys.readouterr().out == f"{Path('custom/model.onnx')}\n"


def test_fetch_effnet_uses_default_path(monkeypatch, capsys) -> None:
    captured = {}

    def fake_fetch(path):
        captured["path"] = path
        return path

    monkeypatch.setattr("soundmind.cli.main.fetch_effnet_model", fake_fetch)

    assert main(["model", "fetch-effnet"]) == 0

    assert captured["path"] == Path("data/models/discogs-effnet-bsdynamic-1.onnx")
    assert capsys.readouterr().out == f"{Path('data/models/discogs-effnet-bsdynamic-1.onnx')}\n"


def test_model_requires_subcommand() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["model"])

    assert exc_info.value.code == 2


def test_learned_rebuild_parser_defaults() -> None:
    args = build_parser().parse_args(["learned-index", "rebuild"])

    assert args.command == "learned-index"
    assert args.learned_command == "rebuild"
    assert args.db == Path("data/database/soundmind.db")
    assert args.model == Path("data/models/discogs-effnet-bsdynamic-1.onnx")
    assert args.index == Path("data/index/effnet_vectors")
    assert args.limit is None


def test_learned_rebuild_forwards_config_and_renders_count(monkeypatch, capsys) -> None:
    captured = {}

    class FakeService:
        def __init__(self, session, *, model_path, index_path) -> None:
            captured["session"] = session
            captured["model_path"] = model_path
            captured["index_path"] = index_path

        def rebuild(self, *, limit=None):
            captured["limit"] = limit
            return 4

    monkeypatch.setattr("soundmind.cli.main.LearnedEmbeddingService", FakeService)
    _stub_session_factory(monkeypatch, captured)

    assert (
        main(
            [
                "learned-index",
                "rebuild",
                "--db",
                "custom.db",
                "--model",
                "custom.onnx",
                "--index",
                "custom-index",
                "--limit",
                "25",
            ]
        )
        == 0
    )

    assert captured["db"] == Path("custom.db")
    assert isinstance(captured["session"], _FakeSession)
    assert captured["model_path"] == Path("custom.onnx")
    assert captured["index_path"] == Path("custom-index")
    assert captured["limit"] == 25
    assert capsys.readouterr().out == "Indexed learned embeddings: 4\n"


def test_learned_rebuild_defaults_limit_to_none(monkeypatch, capsys) -> None:
    captured = {}

    class FakeService:
        def __init__(self, session, *, model_path, index_path) -> None:
            pass

        def rebuild(self, *, limit=None):
            captured["limit"] = limit
            return 0

    monkeypatch.setattr("soundmind.cli.main.LearnedEmbeddingService", FakeService)
    _stub_session_factory(monkeypatch, captured)

    assert main(["learned-index", "rebuild"]) == 0

    assert captured["limit"] is None
    assert capsys.readouterr().out == "Indexed learned embeddings: 0\n"


def test_learned_similar_parser_defaults() -> None:
    args = build_parser().parse_args(["learned-index", "similar", "track-a"])

    assert args.command == "learned-index"
    assert args.learned_command == "similar"
    assert args.track_id == "track-a"
    assert args.db == Path("data/database/soundmind.db")
    assert args.model == Path("data/models/discogs-effnet-bsdynamic-1.onnx")
    assert args.index == Path("data/index/effnet_vectors")
    assert args.limit == 10


def test_learned_similar_renders_tracks_in_order(monkeypatch, capsys) -> None:
    captured = {}

    class FakeService:
        def __init__(self, session, *, model_path, index_path) -> None:
            captured["session"] = session
            captured["model_path"] = model_path
            captured["index_path"] = index_path

        def similar(self, track_id, *, limit=10):
            captured["track_id"] = track_id
            captured["limit"] = limit
            return (
                SimpleNamespace(track_id="track-b", score=0.9),
                SimpleNamespace(track_id="track-c", score=0.123456789),
            )

    monkeypatch.setattr("soundmind.cli.main.LearnedEmbeddingService", FakeService)
    _stub_session_factory(monkeypatch, captured)

    assert (
        main(
            [
                "learned-index",
                "similar",
                "track-a",
                "--db",
                "custom.db",
                "--model",
                "custom.onnx",
                "--index",
                "custom-index",
                "--limit",
                "5",
            ]
        )
        == 0
    )

    assert captured["db"] == Path("custom.db")
    assert isinstance(captured["session"], _FakeSession)
    assert captured["model_path"] == Path("custom.onnx")
    assert captured["index_path"] == Path("custom-index")
    assert captured["track_id"] == "track-a"
    assert captured["limit"] == 5
    assert capsys.readouterr().out == "track-b\t0.900000\ntrack-c\t0.123457\n"


def test_learned_similar_requires_track_id() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["learned-index", "similar"])

    assert exc_info.value.code == 2


def test_learned_index_requires_subcommand() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["learned-index"])

    assert exc_info.value.code == 2


def test_learned_similar_rejects_non_integer_limit() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["learned-index", "similar", "track-a", "--limit", "many"])

    assert exc_info.value.code == 2
