from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from soundmind.cli.main import build_parser, main


def test_recommend_parser_captures_options() -> None:
    args = build_parser().parse_args(
        [
            "recommend",
            "cinematic BGM for coding",
            "--context",
            "coding",
            "--db",
            "library.db",
            "--limit",
            "6",
            "--catalog-limit",
            "20",
            "--event-limit",
            "50",
            "--mode",
            "journey",
            "--now",
            "2026-09-29T12:00:00+05:30",
        ]
    )

    assert args.command == "recommend"
    assert args.text == "cinematic BGM for coding"
    assert args.context == "coding"
    assert args.limit == 6
    assert args.catalog_limit == 20
    assert args.event_limit == 50
    assert args.mode == "journey"
    assert args.now == datetime(2026, 9, 29, 6, 30, tzinfo=UTC)


def test_recommend_parser_requires_timezone_for_now() -> None:
    parser = build_parser()

    try:
        parser.parse_args(
            [
                "recommend",
                "cinematic BGM",
                "--context",
                "coding",
                "--now",
                "2026-09-29T12:00:00",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse failure")


def test_recommend_dispatches_to_catalog_service(monkeypatch, capsys) -> None:
    captured = {}

    class FakeService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def recommend(self, request, **kwargs):
            captured["request"] = request
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(
                    SimpleNamespace(track_id="track-a", score=0.75),
                    SimpleNamespace(track_id="track-b", score=0.5),
                ),
                playlist=(
                    SimpleNamespace(track_id="track-a"),
                    SimpleNamespace(track_id="track-b"),
                ),
            )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "soundmind.cli.main.CatalogContextRecommendationService",
        FakeService,
    )
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    now = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    rc = main(
        [
            "recommend",
            "cinematic BGM",
            "--context",
            "coding",
            "--db",
            "library.db",
            "--limit",
            "2",
            "--catalog-limit",
            "20",
            "--event-limit",
            "50",
            "--mode",
            "discovery",
            "--now",
            now.isoformat(),
        ]
    )

    assert rc == 0
    assert captured["request"].text == "cinematic BGM"
    assert captured["request"].limit == 2
    assert captured["request"].mode.value == "discovery"
    assert captured["kwargs"] == {
        "context": "coding",
        "now": now,
        "event_limit": 50,
        "catalog_limit": 20,
        "seed_track_id": None,
    }

    output = capsys.readouterr().out
    assert "Intent: cinematic BGM" in output
    assert "1. track-a\t0.750000" in output
    assert "2. track-b\t0.500000" in output
    assert "Playlist:" in output
    assert "1. track-a" in output
    assert "2. track-b" in output


def test_recommend_seed_builds_learned_flow(monkeypatch, capsys) -> None:
    captured = {}

    class FakeLearnedService:
        def __init__(self, session, *, model_path, index_path) -> None:
            captured["learned_args"] = (session, model_path, index_path)

    class FakeLearnedEngine:
        def __init__(self, provider) -> None:
            captured["provider"] = provider

    class FakeFlow:
        def __init__(self, *, learned) -> None:
            captured["flow_learned"] = learned

    class FakeRecommendationService:
        def __init__(self, session, *, flow=None) -> None:
            captured["service_flow"] = flow

        def recommend(self, request, **kwargs):
            captured["request"] = request
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(),
                playlist=(),
            )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.LearnedEmbeddingService", FakeLearnedService)
    monkeypatch.setattr("soundmind.cli.main.LearnedRetrievalEngine", FakeLearnedEngine)
    monkeypatch.setattr("soundmind.cli.main.ContextAwareMusicFlow", FakeFlow)
    monkeypatch.setattr(
        "soundmind.cli.main.CatalogContextRecommendationService",
        FakeRecommendationService,
    )
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    rc = main(
        [
            "recommend",
            "similar to this",
            "--context",
            "coding",
            "--seed-track-id",
            "seed-track",
            "--model",
            "custom.onnx",
            "--index",
            "custom-index",
            "--now",
            "2026-09-29T12:00:00Z",
        ]
    )

    assert rc == 0
    assert captured["request"].limit == 10
    assert captured["kwargs"]["seed_track_id"] == "seed-track"
    assert captured["learned_args"][1] == Path("custom.onnx")
    assert captured["learned_args"][2] == Path("custom-index")
    assert captured["service_flow"] is captured["flow_learned"]
    assert isinstance(captured["provider"], FakeLearnedService)
    assert capsys.readouterr().out.startswith("Intent: similar to this")


def test_recommend_without_seed_does_not_construct_learned_service(monkeypatch) -> None:
    class ExplodingLearnedService:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("learned service should not be constructed without a seed")

    class FakeService:
        def __init__(self, session, *, flow=None) -> None:
            assert flow is None

        def recommend(self, request, **kwargs):
            assert kwargs["seed_track_id"] is None
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(),
                playlist=(),
            )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.LearnedEmbeddingService", ExplodingLearnedService)
    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert main(["recommend", "cinematic BGM", "--context", "coding"]) == 0
