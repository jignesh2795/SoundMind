import pytest

from soundmind.playlist_edit_resolution import resolve_playlist_edit_references
from soundmind.playlist_editing import (
    MoveTrack,
    MoveTrackAfter,
    MoveTrackBefore,
    RemoveTrack,
    SwapTracks,
    TrimPlaylist,
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


def playlist() -> tuple[SequenceItem, ...]:
    return (item("track-a"), item("track-b"), item("track-c"))


def rows() -> tuple[object, ...]:
    return (
        type(
            "Row",
            (),
            {
                "track_id": "track-a",
                "title": "Hero Theme",
                "file_name": "hero-theme.mp3",
                "status": "active",
            },
        )(),
        type(
            "Row",
            (),
            {
                "track_id": "track-b",
                "title": "Night Drive",
                "file_name": "night-drive.mp3",
                "status": "active",
            },
        )(),
        type(
            "Row",
            (),
            {
                "track_id": "track-c",
                "title": "Hero Theme",
                "file_name": "hero-theme-live.mp3",
                "status": "active",
            },
        )(),
    )


def test_existing_track_id_reference_is_preserved() -> None:
    session = FakeSession(rows())
    assert resolve_playlist_edit_references(
        session,
        playlist(),
        [RemoveTrack("track-b")],
    ) == (RemoveTrack("track-b"),)


def test_exact_title_reference_resolves_case_insensitively() -> None:
    session = FakeSession(
        tuple(row for row in rows() if row.track_id != "track-c")
    )
    assert resolve_playlist_edit_references(
        session,
        playlist()[:2],
        [RemoveTrack("  hero   theme ")],
    ) == (RemoveTrack("track-a"),)


def test_exact_filename_reference_resolves() -> None:
    session = FakeSession(rows())
    assert resolve_playlist_edit_references(
        session,
        playlist(),
        [MoveTrack("night-drive.mp3", 0)],
    ) == (MoveTrack("track-b", 0),)


def test_relative_and_swap_references_are_all_resolved() -> None:
    session = FakeSession(
        tuple(row for row in rows() if row.track_id != "track-c")
    )
    edits = [
        MoveTrackBefore("Hero Theme", "Night Drive"),
        MoveTrackAfter("track-b", "Hero Theme"),
        SwapTracks("Hero Theme", "track-b"),
        TrimPlaylist(2),
    ]
    assert resolve_playlist_edit_references(session, playlist()[:2], edits) == (
        MoveTrackBefore("track-a", "track-b"),
        MoveTrackAfter("track-b", "track-a"),
        SwapTracks("track-a", "track-b"),
        TrimPlaylist(2),
    )


def test_ambiguous_title_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="ambiguous track reference"):
        resolve_playlist_edit_references(
            FakeSession(rows()),
            playlist(),
            [RemoveTrack("hero theme")],
        )


def test_unknown_reference_is_left_for_editor_validation() -> None:
    assert resolve_playlist_edit_references(
        FakeSession(rows()),
        playlist(),
        [RemoveTrack("future-track")],
    ) == (RemoveTrack("future-track"),)


def test_resolution_does_not_change_input_edits() -> None:
    edits = [RemoveTrack("Hero Theme")]
    result = resolve_playlist_edit_references(
        FakeSession(tuple(row for row in rows() if row.track_id != "track-c")),
        playlist()[:2],
        edits,
    )
    assert edits == [RemoveTrack("Hero Theme")]
    assert result == (RemoveTrack("track-a"),)

def test_resolution_ignores_inactive_catalog_rows() -> None:
    session = FakeSession(
        (
            type(
                "Row",
                (),
                {
                    "track_id": "track-a",
                    "title": "Hero Theme",
                    "file_name": "hero-theme.mp3",
                    "status": "active",
                },
            )(),
            type(
                "Row",
                (),
                {
                    "track_id": "stale-track",
                    "title": "Hero Theme",
                    "file_name": "hero-theme-stale.mp3",
                    "status": "inactive",
                },
            )(),
        )
    )

    assert resolve_playlist_edit_references(
        session,
        (item("track-a"), item("stale-track")),
        [RemoveTrack("Hero Theme")],
    ) == (RemoveTrack("track-a"),)
