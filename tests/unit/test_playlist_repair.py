from soundmind.playlist_repair import plan_playlist_repair
from soundmind.sequence import SequenceItem


def test_plan_playlist_repair_keeps_active_and_removes_stale() -> None:
    items = (
        SequenceItem(track_id="active", sequence_score=1.0, base_score=1.0),
        SequenceItem(track_id="inactive", sequence_score=0.5, base_score=0.5),
        SequenceItem(track_id="missing", sequence_score=0.0, base_score=0.0),
    )

    plan = plan_playlist_repair(
        items,
        {
            "active": "active",
            "inactive": "missing",
        },
    )

    assert [
        (entry.track_id, entry.status, entry.action)
        for entry in plan.entries
    ] == [
        ("active", "active", "keep"),
        ("inactive", "inactive", "remove"),
        ("missing", "missing", "remove"),
    ]
    assert plan.keep_count == 1
    assert plan.remove_count == 2


def test_plan_playlist_repair_preserves_playlist_order() -> None:
    items = (
        SequenceItem(track_id="third", sequence_score=3.0, base_score=3.0),
        SequenceItem(track_id="first", sequence_score=1.0, base_score=1.0),
        SequenceItem(track_id="second", sequence_score=2.0, base_score=2.0),
    )

    plan = plan_playlist_repair(items, {"third": "active", "second": "active"})

    assert [entry.track_id for entry in plan.entries] == [
        "third",
        "first",
        "second",
    ]


def test_plan_playlist_repair_empty_playlist() -> None:
    plan = plan_playlist_repair((), {})

    assert plan.entries == ()
    assert plan.keep_count == 0
    assert plan.remove_count == 0
