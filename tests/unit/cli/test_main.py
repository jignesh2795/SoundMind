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
            self.learned = learned
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
    assert captured["service_flow"].learned is captured["flow_learned"]
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


def test_recommend_explain_prints_signal_contributions(monkeypatch, capsys) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(
                    SimpleNamespace(
                        track_id="track-a",
                        score=0.75,
                        explanation=SimpleNamespace(
                            strongest_signal="preference",
                            contributions=(
                                SimpleNamespace(
                                    name="metadata",
                                    raw_score=0.2,
                                    weight=0.18,
                                    contribution=0.036,
                                ),
                                SimpleNamespace(
                                    name="preference",
                                    raw_score=0.8,
                                    weight=0.18,
                                    contribution=0.144,
                                ),
                            ),
                        ),
                    ),
                ),
                playlist=(SimpleNamespace(track_id="track-a"),),
            )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert (
        main(
            [
                "recommend",
                "cinematic BGM",
                "--context",
                "coding",
                "--explain",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "1. track-a\t0.750000" in output
    assert "strongest: preference" in output
    assert "metadata: raw=0.200000 weight=0.180000 contribution=0.036000" in output
    assert "preference: raw=0.800000 weight=0.180000 contribution=0.144000" in output


def test_search_dispatches_to_catalog_search_service(monkeypatch, capsys) -> None:
    captured = {}

    class FakeSearchService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def search(self, query, *, limit):
            captured["query"] = query
            captured["limit"] = limit
            return (
                SimpleNamespace(
                    track_id="hero-a",
                    score=1.0,
                    title="Hero Entry",
                    artist="Composer A",
                    album="Album A",
                    matched_fields=("title",),
                ),
            )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.CatalogTextSearchService", FakeSearchService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert main(["search", "hero entry", "--db", "library.db", "--limit", "5"]) == 0
    assert captured["query"] == "hero entry"
    assert captured["limit"] == 5
    assert capsys.readouterr().out == (
        "1. hero-a\t1.000000\tHero Entry — Composer A — Album A"
        "\tmatched=title\n"
    )


def test_search_parser_defaults() -> None:
    args = build_parser().parse_args(["search", "hero"])

    assert args.command == "search"
    assert args.query == "hero"
    assert args.limit == 10



def test_search_parser_captures_semantic_options() -> None:
    args = build_parser().parse_args(
        [
            "search",
            "calm cinematic background music",
            "--semantic",
            "--semantic-model",
            "custom-model",
            "--limit",
            "6",
        ]
    )

    assert args.command == "search"
    assert args.query == "calm cinematic background music"
    assert args.semantic is True
    assert args.semantic_model == "custom-model"
    assert args.limit == 6


def test_search_semantic_dispatches_to_catalog_service(monkeypatch, capsys) -> None:
    captured = {}

    class FakeProvider:
        def __init__(self, model_name) -> None:
            captured["model_name"] = model_name

    class FakeSearchService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def semantic_search(self, query, *, provider, limit):
            captured["query"] = query
            captured["provider"] = provider
            captured["limit"] = limit
            return (
                SimpleNamespace(
                    track_id="ambient-a",
                    score=0.912345,
                    title="Calm Hero",
                    artist="Composer A",
                    album="Night BGM",
                ),
            )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.FastEmbedTextProvider", FakeProvider)
    monkeypatch.setattr("soundmind.cli.main.CatalogTextSearchService", FakeSearchService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert (
        main(
            [
                "search",
                "calm cinematic background music",
                "--semantic",
                "--semantic-model",
                "custom-model",
                "--limit",
                "3",
            ]
        )
        == 0
    )
    assert captured["query"] == "calm cinematic background music"
    assert captured["model_name"] == "custom-model"
    assert captured["limit"] == 3
    assert isinstance(captured["provider"], FakeProvider)
    assert capsys.readouterr().out == (
        "1. ambient-a\\t0.912345\\tCalm Hero — Composer A — Night BGM\\tsemantic\\n"
    )
