import pytest

from soundmind.playlist_edit_parser import parse_playlist_edit, parse_playlist_edits
from soundmind.playlist_editing import (
    MoveTrack,
    MoveTrackAfter,
    MoveTrackBefore,
    RemoveTrack,
    SwapTracks,
    TrimPlaylist,
)
from soundmind.playlist_filter import (
    PlaylistFilterAction,
    PlaylistFilterField,
    PlaylistMetadataFilter,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("remove a", RemoveTrack("a")),
        ("delete track 'hero-01'", RemoveTrack("hero-01")),
        ("drop track-a", RemoveTrack("track-a")),
        ("skip b", RemoveTrack("b")),
    ],
)
def test_parse_remove_commands(text: str, expected) -> None:
    assert parse_playlist_edit(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("move a to 1", MoveTrack("a", 0)),
        ("move track b to position 3", MoveTrack("b", 2)),
        ("move 'hero-01' into 2", MoveTrack("hero-01", 1)),
    ],
)
def test_parse_move_commands_use_human_one_based_positions(text: str, expected) -> None:
    assert parse_playlist_edit(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("swap a with b", SwapTracks("a", "b")),
        ("switch track-a and track-b", SwapTracks("track-a", "track-b")),
        ("swap 'hero-01' with 'hero-02'", SwapTracks("hero-01", "hero-02")),
    ],
)
def test_parse_swap_commands(text: str, expected) -> None:
    assert parse_playlist_edit(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("move a before b", MoveTrackBefore("a", "b")),
        ("move track a after track b", MoveTrackAfter("a", "b")),
        ("move 'hero-01' before 'hero-02'", MoveTrackBefore("hero-01", "hero-02")),
    ],
)
def test_parse_relative_move_commands(text: str, expected) -> None:
    assert parse_playlist_edit(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("trim to 5", TrimPlaylist(5)),
        ("trim playlist to 3", TrimPlaylist(3)),
        ("limit playlist to 4", TrimPlaylist(4)),
        ("keep first 2 tracks", TrimPlaylist(2)),
        ("retain the first 6 items", TrimPlaylist(6)),
    ],
)
def test_parse_trim_and_keep_commands(text: str, expected) -> None:
    assert parse_playlist_edit(text) == expected


def test_parser_normalizes_whitespace_without_changing_track_id() -> None:
    assert parse_playlist_edit("  move   HERO-01   to   2  ") == MoveTrack(
        "HERO-01", 1
    )


def test_parse_multiple_commands_preserves_order() -> None:
    assert parse_playlist_edits(
        [
            "remove b",
            "move d to 1",
            "swap d with c",
        ]
    ) == (
        RemoveTrack("b"),
        MoveTrack("d", 0),
        SwapTracks("d", "c"),
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "play something else",
        "move a to 0",
        "move a to -1",
        "move a before a",
        "move a after a",
        "swap a with a",
        "trim to 0",
    ],
)
def test_unsupported_or_invalid_commands_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        parse_playlist_edit(text)


def test_quote_pair_is_removed_only_from_track_id_edges() -> None:
    assert parse_playlist_edit("remove 'track-a'") == RemoveTrack("track-a")
    assert parse_playlist_edit('remove "track-b"') == RemoveTrack("track-b")


def test_unknown_track_text_is_preserved_for_resolution_by_editor() -> None:
    assert parse_playlist_edit("remove future-track") == RemoveTrack("future-track")



@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "remove all tracks by Composer A",
            PlaylistMetadataFilter(
                PlaylistFilterAction.REMOVE,
                PlaylistFilterField.ARTIST,
                "Composer A",
            ),
        ),
        (
            "remove all from album Night Drive",
            PlaylistMetadataFilter(
                PlaylistFilterAction.REMOVE,
                PlaylistFilterField.ALBUM,
                "Night Drive",
            ),
        ),
        (
            "remove all tracks in genre Soundtrack",
            PlaylistMetadataFilter(
                PlaylistFilterAction.REMOVE,
                PlaylistFilterField.GENRE,
                "Soundtrack",
            ),
        ),
        (
            "keep only tracks by Composer A",
            PlaylistMetadataFilter(
                PlaylistFilterAction.KEEP_ONLY,
                PlaylistFilterField.ARTIST,
                "Composer A",
            ),
        ),
        (
            "keep only tracks from album Night Drive",
            PlaylistMetadataFilter(
                PlaylistFilterAction.KEEP_ONLY,
                PlaylistFilterField.ALBUM,
                "Night Drive",
            ),
        ),
        (
            "keep only tracks in genre Soundtrack",
            PlaylistMetadataFilter(
                PlaylistFilterAction.KEEP_ONLY,
                PlaylistFilterField.GENRE,
                "Soundtrack",
            ),
        ),
    ],
)
def test_parse_playlist_metadata_filters(text: str, expected) -> None:
    assert parse_playlist_edit(text) == expected
