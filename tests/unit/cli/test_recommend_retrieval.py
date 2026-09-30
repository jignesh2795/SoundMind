from pathlib import Path
from types import SimpleNamespace

from soundmind.cli.main import build_parser, main


def test_recommend_parser_captures_retrieval_options() -> None:
    args = build_parser().parse_args(
        [
            "recommend",
            "high energy BGM",
            "--context",
            "coding",
            "--retrieval",
            "hybrid-indexed",
            "--retrieval-limit",
            "25",
            "--text-model",
            "model-v2",
            "--text-index",
            "text-index",
            "--lexical-weight",
            "0.8",
            "--semantic-weight",
            "0.2",
        ]
    )

    assert args.retrieval == "hybrid-indexed"
    assert args.retrieval_limit == 25
    assert args.text_model == "model-v2"
    assert args.text_index == Path("text-index")
    assert args.lexical_weight == 0.8
    assert args.semantic_weight == 0.2


def test_recommend_hybrid_dispatches_with_text_provider(monkeypatch, capsys) -> None:
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

    class FakeService:
        def __init__(self, session) -> None:
            pass

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

    monkeypatch.setattr("soundmind.cli.main.FastEmbedTextProvider", FakeProvider)
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
                "high energy BGM",
                "--context",
                "coding",
                "--retrieval",
                "hybrid",
                "--retrieval-limit",
                "25",
                "--text-model",
                "model-v2",
                "--lexical-weight",
                "0.7",
                "--semantic-weight",
                "0.3",
            ]
        )
        == 0
    )

    assert captured["model_name"] == "model-v2"
    assert captured["request"].text == "high energy BGM"
    assert captured["kwargs"]["retrieval_mode"] == "hybrid"
    assert captured["kwargs"]["retrieval_limit"] == 25
    assert captured["kwargs"]["text_provider"].__class__ is FakeProvider
    assert captured["kwargs"]["text_model"] == "model-v2"
    assert captured["kwargs"]["text_index_path"] == Path("data/index/text_vectors")
    assert captured["kwargs"]["lexical_weight"] == 0.7
    assert captured["kwargs"]["semantic_weight"] == 0.3
    assert capsys.readouterr().out == "Intent: high energy BGM\nRanked:\nPlaylist:\n"


def test_recommend_hybrid_indexed_dispatches_to_persisted_path(monkeypatch, capsys) -> None:
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

    class FakeService:
        def __init__(self, session) -> None:
            pass

        def recommend(self, request, **kwargs):
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

    monkeypatch.setattr("soundmind.cli.main.FastEmbedTextProvider", FakeProvider)
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
                "hero entry",
                "--context",
                "coding",
                "--retrieval",
                "hybrid-indexed",
                "--text-model",
                "model-v2",
                "--text-index",
                "custom-index",
                "--lexical-weight",
                "0.25",
                "--semantic-weight",
                "0.75",
            ]
        )
        == 0
    )

    assert captured["model_name"] == "model-v2"
    assert captured["kwargs"]["retrieval_mode"] == "hybrid-indexed"
    assert captured["kwargs"]["text_index_path"] == Path("custom-index")
    assert captured["kwargs"]["text_provider"].__class__ is FakeProvider
    assert captured["kwargs"]["lexical_weight"] == 0.25
    assert captured["kwargs"]["semantic_weight"] == 0.75
    assert capsys.readouterr().out == "Intent: hero entry\nRanked:\nPlaylist:\n"
