from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

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
    assert args.edit == []


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
        def scalars(self, statement):
            return ()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
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
    monkeypatch.setattr(
        "soundmind.cli.main.CatalogContextRecommendationService",
        FakeService,
    )
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

    monkeypatch.setattr(
        "soundmind.cli.main.CatalogContextRecommendationService",
        FakeService,
    )
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

        def search(self, query, *, limit, expand=False):
            captured["query"] = query
            captured["limit"] = limit
            captured["expand"] = expand
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

    assert (
        main(
            [
                "search",
                "hero entry",
                "--expand-query",
                "--db",
                "library.db",
                "--limit",
                "5",
            ]
        )
        == 0
    )
    assert captured["query"] == "hero entry"
    assert captured["limit"] == 5
    assert captured["expand"] is True
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
            "--semantic-query-prefix",
            "",
            "--semantic-document-prefix",
            "",
            "--limit",
            "6",
        ]
    )

    assert args.command == "search"
    assert args.query == "calm cinematic background music"
    assert args.semantic is True
    assert args.semantic_model == "custom-model"
    assert args.semantic_query_prefix == ""
    assert args.semantic_document_prefix == ""
    assert args.limit == 6


def test_search_semantic_dispatches_to_catalog_service(monkeypatch, capsys) -> None:
    captured = {}

    class FakeProvider:
        def __init__(
            self,
            model_name,
            *,
            query_prefix="query: ",
            document_prefix="passage: ",
        ) -> None:
            captured["model_name"] = model_name
            captured["query_prefix"] = query_prefix
            captured["document_prefix"] = document_prefix

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
        "1. ambient-a\t0.912345\tCalm Hero — Composer A — Night BGM\tsemantic\n"
    )


def test_search_parser_supports_persisted_semantic_mode() -> None:
    args = build_parser().parse_args(
        [
            "search",
            "cinematic hero",
            "--semantic-indexed",
            "--semantic-model",
            "model-v1",
            "--semantic-index",
            "text-index",
        ]
    )

    assert args.semantic is False
    assert args.semantic_indexed is True
    assert args.semantic_model == "model-v1"
    assert args.semantic_index == Path("text-index")


def test_search_semantic_modes_are_mutually_exclusive() -> None:
    parser = build_parser()

    try:
        parser.parse_args(["search", "hero", "--semantic", "--semantic-indexed"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse failure")


def test_search_parser_hybrid_defaults() -> None:
    args = build_parser().parse_args(["search", "hero entry"])

    assert args.hybrid is False
    assert args.lexical_weight == 0.5
    assert args.semantic_weight == 0.5


def test_search_hybrid_with_explicit_semantic_stays_live(monkeypatch, capsys) -> None:
    captured = {}

    class FakeProvider:
        def __init__(
            self,
            model_name,
            *,
            query_prefix="query: ",
            document_prefix="passage: ",
        ) -> None:
            pass

    class FakeSearchService:
        def __init__(self, session) -> None:
            pass

        def hybrid_search(self, query, **kwargs):
            captured["live"] = True
            return ()

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

    assert main(["search", "hero", "--hybrid", "--semantic"]) == 0
    assert captured == {"live": True}
    assert capsys.readouterr().out == ""


def test_search_hybrid_dispatches_to_catalog_service(monkeypatch, capsys) -> None:
    captured = {}

    class FakeProvider:
        def __init__(
            self,
            model_name,
            *,
            query_prefix="query: ",
            document_prefix="passage: ",
        ) -> None:
            captured["model_name"] = model_name

    class FakeSearchService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def hybrid_search(
            self,
            query,
            *,
            provider,
            limit,
            lexical_weight,
            semantic_weight,
            expand=False,
        ):
            captured["query"] = query
            captured["expand"] = expand
            captured["provider"] = provider
            captured["limit"] = limit
            captured["weights"] = (lexical_weight, semantic_weight)
            return (
                SimpleNamespace(
                    track_id="hero-a",
                    score=0.9,
                    lexical_score=1.0,
                    semantic_score=0.8,
                    title="Hero Entry",
                    artist="Composer A",
                    album=None,
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
                "hero entry",
                "--hybrid",
                "--lexical-weight",
                "0.7",
                "--semantic-weight",
                "0.3",
                "--limit",
                "5",
            ]
        )
        == 0
    )
    assert captured["query"] == "hero entry"
    assert captured["weights"] == (0.7, 0.3)
    assert captured["expand"] is False
    assert isinstance(captured["provider"], FakeProvider)
    assert capsys.readouterr().out == (
        "1. hero-a\t0.900000\tHero Entry — Composer A"
        "\thybrid lexical=1.000000 semantic=0.800000\n"
    )


def test_search_hybrid_indexed_dispatches_to_catalog_service(monkeypatch, capsys) -> None:
    captured = {}

    class FakeProvider:
        def __init__(
            self,
            model_name,
            *,
            query_prefix="query: ",
            document_prefix="passage: ",
        ) -> None:
            pass

    class FakeSearchService:
        def __init__(self, session) -> None:
            pass

        def hybrid_search_indexed(
            self,
            query,
            *,
            provider,
            model_name,
            index_path,
            query_prefix,
            document_prefix,
            limit,
            lexical_weight,
            semantic_weight,
            expand=False,
        ):
            captured["model_name"] = model_name
            captured["expand"] = expand
            captured["index_path"] = index_path
            return ()

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
                "hero",
                "--hybrid",
                "--semantic-indexed",
                "--semantic-index",
                "text-index",
            ]
        )
        == 0
    )
    assert captured["model_name"] == "BAAI/bge-small-en-v1.5"
    assert captured["index_path"] == Path("text-index")
    assert captured["expand"] is False
    assert capsys.readouterr().out == ""



def test_semantic_index_parser_captures_embedding_profile() -> None:
    args = build_parser().parse_args(
        [
            "semantic-index",
            "rebuild",
            "--model",
            "multilingual-model",
            "--query-prefix",
            "",
            "--document-prefix",
            "",
        ]
    )

    assert args.model == "multilingual-model"
    assert args.query_prefix == ""
    assert args.document_prefix == ""


def test_search_explain_retrieval_prints_lexical_evidence(monkeypatch, capsys) -> None:
    class FakeSearchService:
        def __init__(self, session) -> None:
            pass

        def search(self, query, *, limit, expand=False):
            return (
                SimpleNamespace(
                    track_id="hero",
                    score=1.0,
                    title="Hero Entry",
                    artist="Composer",
                    album=None,
                    matched_fields=("title",),
                    matched_query="hero entry",
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

    assert main(["search", "hero entry", "--explain-retrieval"]) == 0

    assert capsys.readouterr().out == (
        "1. hero\t1.000000\tHero Entry — Composer\tmatched=title\n"
        "   matched-query: hero entry\n"
    )


def test_recommend_parser_captures_repeatable_edit_commands() -> None:
    args = build_parser().parse_args(
        [
            "recommend",
            "cinematic BGM",
            "--context",
            "coding",
            "--edit",
            "remove a",
            "--edit",
            "move d to 1",
        ]
    )

    assert args.edit == ["remove a", "move d to 1"]
    assert args.preview_edits is False


def test_recommend_applies_edits_after_sequencing_without_changing_ranked(monkeypatch, capsys) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(
                    SimpleNamespace(track_id="a", score=0.9),
                    SimpleNamespace(track_id="b", score=0.8),
                    SimpleNamespace(track_id="c", score=0.7),
                    SimpleNamespace(track_id="d", score=0.6),
                ),
                playlist=(
                    SimpleNamespace(track_id="a"),
                    SimpleNamespace(track_id="b"),
                    SimpleNamespace(track_id="c"),
                    SimpleNamespace(track_id="d"),
                ),
            )

    class FakeSession:
        def scalars(self, statement):
            return ()

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
                "--edit",
                "remove b",
                "--edit",
                "move d to 1",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "1. a\t0.900000" in output
    assert "2. b\t0.800000" in output
    assert "3. c\t0.700000" in output
    assert "4. d\t0.600000" in output
    assert "Playlist:" in output
    playlist = output.split("Playlist:", 1)[1]
    assert "1. d" in playlist
    assert "2. a" in playlist
    assert "3. c" in playlist
    assert "4. b" not in playlist


def test_recommend_resolves_exact_catalog_title_before_edit(
    monkeypatch, capsys
) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(
                    SimpleNamespace(track_id="track-a", score=0.9),
                    SimpleNamespace(track_id="track-b", score=0.8),
                ),
                playlist=(
                    SimpleNamespace(track_id="track-a"),
                    SimpleNamespace(track_id="track-b"),
                ),
            )

    class FakeSession:
        def scalars(self, statement):
            return (
                SimpleNamespace(
                    track_id="track-a",
                    title="Hero Theme",
                    file_name="hero-theme.mp3",
                ),
                SimpleNamespace(
                    track_id="track-b",
                    title="Night Drive",
                    file_name="night-drive.mp3",
                ),
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert main(
        [
            "recommend",
            "cinematic BGM",
            "--context",
            "coding",
            "--edit",
            "remove hero theme",
        ]
    ) == 0

    playlist = capsys.readouterr().out.split("Playlist:", 1)[1]
    assert "1. track-b" in playlist
    assert "track-a" not in playlist



def test_recommend_applies_metadata_filter_after_sequencing(
    monkeypatch, capsys
) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(
                    SimpleNamespace(track_id="a", score=0.9),
                    SimpleNamespace(track_id="b", score=0.8),
                    SimpleNamespace(track_id="c", score=0.7),
                ),
                playlist=(
                    SimpleNamespace(track_id="a"),
                    SimpleNamespace(track_id="b"),
                    SimpleNamespace(track_id="c"),
                ),
            )

    class FakeSession:
        def scalars(self, statement):
            return (
                SimpleNamespace(
                    track_id="a",
                    title="Hero",
                    file_name="hero.mp3",
                    artist="A",
                ),
                SimpleNamespace(
                    track_id="b",
                    title="Night",
                    file_name="night.mp3",
                    artist="B",
                ),
                SimpleNamespace(
                    track_id="c",
                    title="Outro",
                    file_name="outro.mp3",
                    artist="A",
                ),
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert main(
        [
            "recommend",
            "cinematic BGM",
            "--context",
            "coding",
            "--edit",
            "remove all tracks by A",
        ]
    ) == 0

    output = capsys.readouterr().out
    playlist = output.split("Playlist:", 1)[1]
    assert "1. b" in playlist
    assert "a" not in playlist
    assert "c" not in playlist



def test_recommend_preview_shows_edit_plan_without_normal_playlist(
    monkeypatch, capsys
) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(
                    SimpleNamespace(track_id="a", score=0.9),
                    SimpleNamespace(track_id="b", score=0.8),
                    SimpleNamespace(track_id="c", score=0.7),
                ),
                playlist=(
                    SimpleNamespace(track_id="a"),
                    SimpleNamespace(track_id="b"),
                    SimpleNamespace(track_id="c"),
                ),
            )

    class FakeSession:
        def scalars(self, statement):
            return ()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    assert main(
        [
            "recommend",
            "cinematic BGM",
            "--context",
            "coding",
            "--edit",
            "remove b",
            "--edit",
            "move c to 1",
            "--preview-edits",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "Ranked:" in output
    assert "Playlist:" not in output
    assert "Edit preview:" in output
    assert "1. command: remove b" in output
    assert "   → remove b" in output
    assert "2. command: move c to position 1" in output
    assert "   → move c to position 1" in output
    assert "Playlist preview:" in output
    preview = output.split("Playlist preview:", 1)[1]
    assert "1. c" in preview
    assert "2. a" in preview
    assert "3. b" not in preview


def test_recommend_preview_requires_edits(monkeypatch) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
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

    monkeypatch.setattr("soundmind.cli.main.CatalogContextRecommendationService", FakeService)
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: lambda: FakeSession(),
    )

    with pytest.raises(ValueError, match="requires at least one --edit"):
        main(["recommend", "cinematic BGM", "--context", "coding", "--preview-edits"])


def test_recommend_preview_shows_deterministic_edit_diff(monkeypatch, capsys) -> None:
    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
            return SimpleNamespace(
                intent=SimpleNamespace(raw_text=request.text),
                ranked=(),
                playlist=(
                    SimpleNamespace(track_id="a"),
                    SimpleNamespace(track_id="b"),
                    SimpleNamespace(track_id="c"),
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

    assert main(
        [
            "recommend",
            "cinematic BGM",
            "--context",
            "coding",
            "--edit",
            "move c to 1",
            "--preview-edits",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "changes:" in output
    assert "move a from position 1 to position 2" in output
    assert "move b from position 2 to position 3" in output
    assert "move c from position 3 to position 1" in output