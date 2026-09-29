from sqlalchemy import select

from soundmind.catalog_search import CatalogTextSearchService
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


def row(track_id: str, *, title: str, artist: str, status: str = "active") -> TrackRow:
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1,
        modified_at_ns=1,
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
