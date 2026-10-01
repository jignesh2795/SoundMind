from datetime import UTC, datetime

import pytest

from soundmind.playlist_storage import PlaylistRepository
from soundmind.sequence import SequenceItem
from soundmind.storage.database import create_session_factory


def item(track_id: str, sequence_score: float, base_score: float) -> SequenceItem:
    return SequenceItem(
        track_id=track_id,
        sequence_score=sequence_score,
        base_score=base_score,
    )


def test_save_and_load_preserves_order_and_scores(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    created = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    items = (item("a", 0.9, 0.8), item("b", 0.7, 0.6))

    with session_factory() as session:
        PlaylistRepository(session).save("  Focus  Music ", items, now=created)
        session.commit()

    with session_factory() as session:
        loaded = PlaylistRepository(session).get("focus music")

    assert loaded is not None
    assert loaded.name == "Focus Music"
    assert loaded.items == items
    assert loaded.created_at == created
    assert loaded.updated_at == created


def test_save_replaces_existing_name_case_insensitively(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    first_time = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    second_time = datetime(2026, 10, 1, 11, 0, tzinfo=UTC)

    with session_factory() as session:
        repository = PlaylistRepository(session)
        first = repository.save("Coding", (item("a", 1.0, 0.9),), now=first_time)
        second = repository.save(
            " coding ",
            (item("b", 0.8, 0.7), item("c", 0.6, 0.5)),
            now=second_time,
        )
        session.commit()

        assert first.name == "Coding"
        assert second.name == "coding"
        assert second.created_at == first_time
        assert second.updated_at == second_time
        assert second.items == (item("b", 0.8, 0.7), item("c", 0.6, 0.5))
        assert len(repository.list()) == 1


def test_list_returns_playlists_in_deterministic_name_order(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    with session_factory() as session:
        repository = PlaylistRepository(session)
        repository.save("Zeta", (item("z", 1.0, 1.0),), now=now)
        repository.save("Alpha", (item("a", 1.0, 1.0),), now=now)
        repository.save("Beta", (item("b", 1.0, 1.0),), now=now)
        session.commit()

        assert [playlist.name for playlist in repository.list()] == [
            "Alpha",
            "Beta",
            "Zeta",
        ]


def test_missing_playlist_returns_none(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        assert PlaylistRepository(session).get("Missing") is None


def test_empty_playlist_is_persisted(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    with session_factory() as session:
        saved = PlaylistRepository(session).save("Empty", (), now=now)
        session.commit()

    with session_factory() as session:
        loaded = PlaylistRepository(session).get("empty")

    assert saved.items == ()
    assert loaded is not None
    assert loaded.items == ()


def test_invalid_playlist_name_and_duplicate_track_are_rejected(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        repository = PlaylistRepository(session)
        with pytest.raises(ValueError, match="playlist name"):
            repository.save("   ", ())
        with pytest.raises(ValueError, match="duplicate track_id"):
            repository.save(
                "Duplicate",
                (item("a", 1.0, 1.0), item("a", 0.5, 0.4)),
            )