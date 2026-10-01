import pytest

from soundmind.playlist_editing import (
    MoveTrack,
    MoveTrackAfter,
    MoveTrackBefore,
    RemoveTrack,
    SwapTracks,
    TrimPlaylist,
    apply_playlist_edits,
)
from soundmind.sequence import SequenceItem


def item(track_id: str, score: float) -> SequenceItem:
    return SequenceItem(
        track_id=track_id,
        sequence_score=score,
        base_score=score,
    )


def playlist() -> tuple[SequenceItem, ...]:
    return (item("a", 1.0), item("b", 0.8), item("c", 0.6), item("d", 0.4))


def test_remove_track_preserves_remaining_items() -> None:
    assert [x.track_id for x in apply_playlist_edits(playlist(), [RemoveTrack("b")])] == [
        "a",
        "c",
        "d",
    ]


def test_move_track_uses_zero_based_absolute_position() -> None:
    result = apply_playlist_edits(playlist(), [MoveTrack("d", 1)])
    assert [x.track_id for x in result] == ["a", "d", "b", "c"]


def test_move_track_before_target() -> None:
    result = apply_playlist_edits(playlist(), [MoveTrackBefore("d", "b")])
    assert [x.track_id for x in result] == ["a", "d", "b", "c"]


def test_move_track_after_target() -> None:
    result = apply_playlist_edits(playlist(), [MoveTrackAfter("a", "c")])
    assert [x.track_id for x in result] == ["b", "c", "a", "d"]


def test_swap_tracks_exchanges_positions() -> None:
    result = apply_playlist_edits(playlist(), [SwapTracks("a", "c")])
    assert [x.track_id for x in result] == ["c", "b", "a", "d"]


def test_trim_playlist_keeps_prefix() -> None:
    result = apply_playlist_edits(playlist(), [TrimPlaylist(2)])
    assert [x.track_id for x in result] == ["a", "b"]


def test_edits_are_applied_sequentially() -> None:
    result = apply_playlist_edits(
        playlist(),
        [RemoveTrack("b"), MoveTrack("d", 0), SwapTracks("d", "c")],
    )
    assert [x.track_id for x in result] == ["c", "a", "d"]


def test_input_playlist_is_not_mutated() -> None:
    original = playlist()
    apply_playlist_edits(original, [RemoveTrack("b"), MoveTrack("d", 0)])
    assert [x.track_id for x in original] == ["a", "b", "c", "d"]


def test_duplicate_input_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate track_id"):
        apply_playlist_edits((item("a", 1.0), item("a", 0.5)), [])


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (RemoveTrack("missing"), "not found"),
        (MoveTrack("missing", 0), "not found"),
        (MoveTrack("a", -1), "position"),
        (MoveTrackBefore("a", "missing"), "not found"),
        (MoveTrackAfter("a", "missing"), "not found"),
        (MoveTrackBefore("a", "a"), "distinct"),
        (MoveTrackAfter("a", "a"), "distinct"),
        (SwapTracks("a", "missing"), "not found"),
        (SwapTracks("a", "a"), "distinct"),
        (TrimPlaylist(0), "limit"),
    ],
)
def test_invalid_edits_are_rejected(edit, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        apply_playlist_edits(playlist(), [edit])


def test_move_to_last_position_is_supported() -> None:
    result = apply_playlist_edits(playlist(), [MoveTrack("a", 3)])
    assert [x.track_id for x in result] == ["b", "c", "d", "a"]
