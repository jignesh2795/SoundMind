from datetime import UTC, datetime

import pytest

from soundmind.recommendation.semantic_text_retrieval import (
    SemanticTextRetrievalEngine,
    catalog_text,
)
from soundmind.storage.models import TrackRow


def row(
    track_id: str,
    *,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    genre: str | None = None,
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
        album=album,
        genre=genre,
    )


class FakeProvider:
    def __init__(self, query_vector, document_vectors):
        self.query_vector = query_vector
        self.document_vectors = document_vectors
        self.query_text = None
        self.documents = None

    def embed_query(self, text):
        self.query_text = text
        return self.query_vector

    def embed_documents(self, texts):
        self.documents = tuple(texts)
        return self.document_vectors


def test_catalog_text_is_stable_and_labeled() -> None:
    item = row(
        "hero",
        title="Hero Entry",
        artist="Composer",
        album="Action BGM",
        genre="Cinematic",
    )

    assert catalog_text(item) == (
        "title: Hero Entry | artist: Composer | album: Action BGM | "
        "genre: Cinematic | file name: hero.mp3"
    )


def test_semantic_search_ranks_by_cosine_similarity() -> None:
    provider = FakeProvider(
        query_vector=(1.0, 0.0),
        document_vectors=((1.0, 0.0), (0.6, 0.8), (-1.0, 0.0)),
    )
    items = [
        row("close", title="Cinematic action"),
        row("medium", title="Calm"),
        row("far", title="Comedy"),
    ]

    results = SemanticTextRetrievalEngine(provider).search("epic battle", items)

    assert [item.track_id for item in results] == ["close", "medium", "far"]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(0.6)
    assert results[2].score == pytest.approx(-1.0)
    assert provider.query_text == "epic battle"
    assert provider.documents == tuple(catalog_text(item) for item in items)


def test_semantic_search_excludes_inactive_rows_and_tiebreaks_by_track_id() -> None:
    provider = FakeProvider(
        query_vector=(1.0, 0.0),
        document_vectors=((1.0, 0.0), (1.0, 0.0)),
    )
    items = [
        row("b", title="Hero", status="active"),
        row("hidden", title="Hero", status="missing"),
        row("a", title="Hero", status="active"),
    ]

    results = SemanticTextRetrievalEngine(provider).search("hero", items)

    assert [item.track_id for item in results] == ["a", "b"]
    assert all(item.track_id != "hidden" for item in results)
    assert len(provider.documents) == 2


@pytest.mark.parametrize(
    ("query", "limit"),
    [
        ("", 10),
        ("   ", 10),
        ("hero", 0),
        ("hero", -1),
        ("hero", True),
    ],
)
def test_semantic_search_rejects_invalid_input(query: str, limit: int) -> None:
    provider = FakeProvider((1.0,), ())
    with pytest.raises(ValueError):
        SemanticTextRetrievalEngine(provider).search(query, [], limit=limit)


def test_semantic_search_rejects_wrong_document_count() -> None:
    provider = FakeProvider((1.0,), ())
    items = [row("hero", title="Hero")]

    with pytest.raises(ValueError, match="document count"):
        SemanticTextRetrievalEngine(provider).search("hero", items)


def test_semantic_search_rejects_embedding_dimension_mismatch() -> None:
    provider = FakeProvider(
        query_vector=(1.0, 0.0),
        document_vectors=((1.0,),),
    )
    items = [row("hero", title="Hero")]

    with pytest.raises(ValueError, match="dimensions"):
        SemanticTextRetrievalEngine(provider).search("hero", items)


def test_semantic_search_maps_zero_norm_vectors_to_zero() -> None:
    provider = FakeProvider(
        query_vector=(1.0, 0.0),
        document_vectors=((0.0, 0.0),),
    )
    items = [row("hero", title="Hero")]

    results = SemanticTextRetrievalEngine(provider).search("hero", items)

    assert results[0].score == 0.0
