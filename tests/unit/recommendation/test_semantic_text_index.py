from datetime import UTC, datetime
from pathlib import Path

import pytest

from soundmind.recommendation.semantic_text_index import (
    PersistentSemanticTextIndex,
    SemanticIndexStaleError,
)
from soundmind.storage.models import TrackRow


def row(
    track_id: str,
    *,
    title: str,
    artist: str = "Composer",
    status: str = "active",
) -> TrackRow:
    now = datetime.now(UTC)
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1,
        modified_at_ns=1,
        status=status,
        created_at=now,
        updated_at=now,
        title=title,
        artist=artist,
    )


class FakeProvider:
    def __init__(self) -> None:
        self.document_calls = 0
        self.query_calls = 0

    def embed_documents(self, texts):
        self.document_calls += 1
        return tuple(
            (1.0, 0.0) if "hero" in text.casefold() else (0.0, 1.0)
            for text in texts
        )

    def embed_query(self, text):
        self.query_calls += 1
        return (1.0, 0.0)


def test_rebuild_persists_catalog_vectors_and_manifest(tmp_path: Path) -> None:
    provider = FakeProvider()
    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [
        row("b", title="Calm"),
        row("a", title="Hero Entry"),
        row("hidden", title="Hero", status="missing"),
    ]

    assert index.rebuild(rows, provider=provider, model_name="model-v1") == 2
    assert provider.document_calls == 1
    assert index.path.with_suffix(".vectors.npy").exists()
    assert index.path.with_suffix(".ids.npy").exists()
    assert index.manifest_path.exists()


def test_search_uses_persisted_vectors_and_only_embeds_query(tmp_path: Path) -> None:
    provider = FakeProvider()
    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [row("hero", title="Hero Entry"), row("calm", title="Calm")]

    index.rebuild(rows, provider=provider, model_name="model-v1")
    provider.document_calls = 0

    results = index.search(
        "cinematic hero",
        rows,
        provider=provider,
        model_name="model-v1",
        limit=10,
    )

    assert results == [("hero", 1.0), ("calm", 0.0)]
    assert provider.document_calls == 0
    assert provider.query_calls == 1


def test_search_rejects_stale_catalog_and_model(tmp_path: Path) -> None:
    provider = FakeProvider()
    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [row("hero", title="Hero Entry")]

    index.rebuild(rows, provider=provider, model_name="model-v1")

    with pytest.raises(SemanticIndexStaleError, match="catalog"):
        index.search(
            "hero",
            [row("hero", title="Changed Entry")],
            provider=provider,
            model_name="model-v1",
        )

    with pytest.raises(SemanticIndexStaleError, match="model"):
        index.search(
            "hero",
            rows,
            provider=provider,
            model_name="model-v2",
        )


def test_rebuild_rejects_inconsistent_dimensions(tmp_path: Path) -> None:
    class RaggedProvider(FakeProvider):
        def embed_documents(self, texts):
            return ((1.0, 0.0), (0.0,))

    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [row("a", title="Hero Entry"), row("b", title="Calm")]

    with pytest.raises(ValueError, match="inconsistent dimensions"):
        index.rebuild(rows, provider=RaggedProvider(), model_name="model-v1")


def test_rebuild_rejects_non_finite_values(tmp_path: Path) -> None:
    class NonFiniteProvider(FakeProvider):
        def embed_documents(self, texts):
            return ((1.0, float("nan")), (0.0, 1.0))

    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [row("a", title="Hero Entry"), row("b", title="Calm")]

    with pytest.raises(ValueError, match="finite"):
        index.rebuild(rows, provider=NonFiniteProvider(), model_name="model-v1")


def test_rebuild_is_deterministic_for_same_catalog(tmp_path: Path) -> None:
    provider = FakeProvider()
    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [row("b", title="Calm"), row("a", title="Hero Entry")]

    index.rebuild(rows, provider=provider, model_name="model-v1")
    first = index.manifest_path.read_text(encoding="utf-8")
    index.rebuild(rows, provider=provider, model_name="model-v1")
    second = index.manifest_path.read_text(encoding="utf-8")

    assert first == second
    assert "catalog_fingerprint" in first



def test_search_rejects_changed_embedding_prompt_configuration(tmp_path: Path) -> None:
    provider = FakeProvider()
    index = PersistentSemanticTextIndex(tmp_path / "semantic_vectors")
    rows = [row("hero", title="Hero Entry")]

    index.rebuild(
        rows,
        provider=provider,
        model_name="model-v1",
        query_prefix="",
        document_prefix="",
    )

    with pytest.raises(SemanticIndexStaleError, match="prompt configuration"):
        index.search(
            "hero",
            rows,
            provider=provider,
            model_name="model-v1",
        )
