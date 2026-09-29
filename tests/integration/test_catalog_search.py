from datetime import UTC, datetime

from sqlalchemy import select

from soundmind.catalog_search import CatalogTextSearchService
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


def row(track_id: str, *, title: str, artist: str, status: str = "active") -> TrackRow:
    now = datetime.now(UTC)
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1,
        modified_at_ns=1,
        created_at=now,
        updated_at=now,
        status=status,
        title=title,
        artist=artist,
    )


def test_sqlite_catalog_search_reads_active_rows_and_returns_matches(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all(
            [
                row("hero-a", title="Mass Hero Entry", artist="Composer A"),
                row("hero-b", title="Hero Theme", artist="Composer B"),
                row("hidden", title="Hero Entry", artist="Composer C", status="missing"),
            ]
        )
        session.commit()

        results = CatalogTextSearchService(session).search("hero entry", limit=10)

    assert [result.track_id for result in results] == ["hero-a", "hero-b"]
    assert results[0].title == "Mass Hero Entry"
    assert results[0].artist == "Composer A"
    assert results[0].matched_fields == ("title",)
    assert results[1].score == 0.5


def test_sqlite_catalog_search_does_not_mutate_catalog(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(row("hero", title="Hero Entry", artist="Composer"))
        session.commit()

        CatalogTextSearchService(session).search("hero")
        session.expire_all()

        stored = session.scalars(select(TrackRow)).all()

    assert [(item.track_id, item.title) for item in stored] == [
        ("hero", "Hero Entry")
    ]


class FakeProvider:
    def embed_query(self, text):
        return (1.0, 0.0)

    def embed_documents(self, texts):
        assert texts[0].startswith("title: Hero")
        return ((1.0, 0.0), (0.0, 1.0))


def test_sqlite_catalog_semantic_search_uses_active_rows(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all(
            [
                row("hero", title="Hero Entry", artist="Composer A"),
                row("other", title="Other Theme", artist="Composer B"),
                row("hidden", title="Hero", artist="Composer C", status="missing"),
            ]
        )
        session.commit()

        results = CatalogTextSearchService(session).semantic_search(
            "cinematic hero",
            provider=FakeProvider(),
            limit=10,
        )

    assert [result.track_id for result in results] == ["hero", "other"]
    assert results[0].score == 1.0
    assert results[0].title == "Hero Entry"
    assert results[1].score == 0.0


class IndexedFakeProvider:
    def __init__(self) -> None:
        self.document_calls = 0
        self.query_calls = 0

    def embed_documents(self, texts):
        self.document_calls += 1
        return tuple((1.0, 0.0) if "hero" in text.casefold() else (0.0, 1.0) for text in texts)

    def embed_query(self, text):
        self.query_calls += 1
        return (1.0, 0.0)


def test_sqlite_catalog_persisted_semantic_search_reuses_index(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    index_path = tmp_path / "text_vectors"
    provider = IndexedFakeProvider()

    with session_factory() as session:
        session.add_all(
            [
                row("hero", title="Hero Entry", artist="Composer A"),
                row("calm", title="Calm Theme", artist="Composer B"),
            ]
        )
        session.commit()
        service = CatalogTextSearchService(session)
        assert service.rebuild_semantic_index(
            provider=provider,
            model_name="model-v1",
            index_path=index_path,
        ) == 2
        provider.document_calls = 0

        results = service.semantic_search_indexed(
            "cinematic hero",
            provider=provider,
            model_name="model-v1",
            index_path=index_path,
            limit=10,
        )

    assert [item.track_id for item in results] == ["hero", "calm"]
    assert results[0].score == 1.0
    assert provider.document_calls == 0
    assert provider.query_calls == 1
