from soundmind.playlist_edit_parser import parse_playlist_edits
from soundmind.playlist_edit_workflow import apply_playlist_edit_commands
from soundmind.sequence import SequenceItem


def item(track_id: str) -> SequenceItem:
    return SequenceItem(track_id=track_id, sequence_score=1.0, base_score=1.0)


class FakeSession:
    def __init__(self, rows) -> None:
        self.rows = rows

    def scalars(self, statement):
        return self.rows


def row(track_id: str, *, artist: str):
    return type(
        "Row",
        (),
        {
            "track_id": track_id,
            "title": None,
            "file_name": f"{track_id}.mp3",
            "artist": artist,
        },
    )()


def test_filter_uses_current_playlist_after_previous_edit() -> None:
    session = FakeSession(
        (
            row("a", artist="Composer A"),
            row("b", artist="Composer B"),
            row("c", artist="Composer A"),
        )
    )
    commands = parse_playlist_edits(
        [
            "remove a",
            "keep only tracks by Composer A",
        ]
    )
    result = apply_playlist_edit_commands(
        session,
        (item("a"), item("b"), item("c")),
        commands,
    )
    assert [item.track_id for item in result] == ["c"]


def test_structural_and_filter_commands_compose_in_order() -> None:
    session = FakeSession(
        (
            row("a", artist="Composer A"),
            row("b", artist="Composer B"),
            row("c", artist="Composer A"),
        )
    )
    commands = parse_playlist_edits(
        [
            "move c before b",
            "remove all tracks by Composer B",
        ]
    )
    result = apply_playlist_edit_commands(
        session,
        (item("a"), item("b"), item("c")),
        commands,
    )
    assert [item.track_id for item in result] == ["a", "c"]
