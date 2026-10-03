import pytest

from soundmind.playlist_editing import RemoveTrack
from soundmind.playlist_filter import (
    PlaylistFilterAction,
    PlaylistFilterField,
    PlaylistMetadataFilter,
    playlist_filter_to_edits,
)
from soundmind.sequence import SequenceItem


def item(track_id: str) -> SequenceItem:
    return SequenceItem(track_id=track_id, sequence_score=1.0, base_score=1.0)


class FakeSession:
    def __init__(self, rows) -> None:
        self.rows = rows

    def scalars(self, statement):
        rendered = str(statement.compile(compile_kwargs={"literal_binds": True}))
        if "tracks.status = 'active'" not in rendered:
            return self.rows
        return tuple(row for row in self.rows if row.status == "active")


def row(
    track_id: str,
    *,
    artist=None,
    album=None,
    genre=None,
    status="active",
):
    return type(
        "Row",
        (),
        {
            "track_id": track_id,
            "artist": artist,
            "album": album,
            "genre": genre,
            "status": status,
        },
    )()


def test_remove_artist_matches_exactly_and_preserves_playlist_order() -> None:
    session = FakeSession(
        (
            row("a", artist="Composer A"),
            row("b", artist="Composer B"),
            row("c", artist="Composer A"),
        )
    )
    result = playlist_filter_to_edits(
        session,
        (item("a"), item("b"), item("c")),
        PlaylistMetadataFilter(
            PlaylistFilterAction.REMOVE,
            PlaylistFilterField.ARTIST,
            "composer a",
        ),
    )
    assert result == (RemoveTrack("a"), RemoveTrack("c"))


def test_remove_album_matches_normalized_whitespace() -> None:
    session = FakeSession(
        (
            row("a", album="Night  Drive"),
            row("b", album="Day Drive"),
        )
    )
    result = playlist_filter_to_edits(
        session,
        (item("a"), item("b")),
        PlaylistMetadataFilter(
            PlaylistFilterAction.REMOVE,
            PlaylistFilterField.ALBUM,
            "  night drive ",
        ),
    )
    assert result == (RemoveTrack("a"),)


def test_genre_filter_matches_one_of_comma_separated_genres() -> None:
    session = FakeSession(
        (
            row("a", genre="Soundtrack, BGM"),
            row("b", genre="Rock"),
            row("c", genre="BGM"),
        )
    )
    result = playlist_filter_to_edits(
        session,
        (item("a"), item("b"), item("c")),
        PlaylistMetadataFilter(
            PlaylistFilterAction.REMOVE,
            PlaylistFilterField.GENRE,
            "bgm",
        ),
    )
    assert result == (RemoveTrack("a"), RemoveTrack("c"))


def test_keep_only_artist_removes_non_matches() -> None:
    session = FakeSession(
        (
            row("a", artist="Composer A"),
            row("b", artist="Composer B"),
            row("c", artist="Composer A"),
        )
    )
    result = playlist_filter_to_edits(
        session,
        (item("a"), item("b"), item("c")),
        PlaylistMetadataFilter(
            PlaylistFilterAction.KEEP_ONLY,
            PlaylistFilterField.ARTIST,
            "Composer A",
        ),
    )
    assert result == (RemoveTrack("b"),)


def test_keep_only_with_no_matches_removes_entire_playlist() -> None:
    session = FakeSession((row("a", artist="Composer A"),))
    result = playlist_filter_to_edits(
        session,
        (item("a"),),
        PlaylistMetadataFilter(
            PlaylistFilterAction.KEEP_ONLY,
            PlaylistFilterField.ARTIST,
            "Composer B",
        ),
    )
    assert result == (RemoveTrack("a"),)


def test_empty_playlist_requires_no_catalog_query() -> None:
    session = FakeSession(())
    result = playlist_filter_to_edits(
        session,
        (),
        PlaylistMetadataFilter(
            PlaylistFilterAction.REMOVE,
            PlaylistFilterField.ARTIST,
            "Composer A",
        ),
    )
    assert result == ()


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (
            PlaylistMetadataFilter(
                PlaylistFilterAction.REMOVE,
                PlaylistFilterField.ARTIST,
                "",
            ),
            "filter value",
        ),
    ],
)
def test_invalid_filter_values_are_rejected(edit, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        playlist_filter_to_edits(FakeSession(()), (item("a"),), edit)

def test_remove_filter_ignores_inactive_catalog_rows() -> None:
    session = FakeSession(
        (
            row("active", artist="Composer A", status="active"),
            row("inactive", artist="Composer A", status="inactive"),
        )
    )

    result = playlist_filter_to_edits(
        session,
        (item("active"), item("inactive")),
        PlaylistMetadataFilter(
            PlaylistFilterAction.REMOVE,
            PlaylistFilterField.ARTIST,
            "Composer A",
        ),
    )

    assert result == (RemoveTrack("active"),)
