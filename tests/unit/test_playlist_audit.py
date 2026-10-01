from soundmind.playlist_audit import audit_playlist
from soundmind.sequence import SequenceItem


def test_audit_playlist_classifies_active_inactive_and_missing() -> None:
    items = (
        SequenceItem(track_id="active", sequence_score=1.0, base_score=1.0),
        SequenceItem(track_id="inactive", sequence_score=0.5, base_score=0.5),
        SequenceItem(track_id="missing", sequence_score=0.0, base_score=0.0),
    )

    report = audit_playlist(
        items,
        {
            "active": "active",
            "inactive": "missing",
        },
    )

    assert [(entry.track_id, entry.status) for entry in report.entries] == [
        ("active", "active"),
        ("inactive", "inactive"),
        ("missing", "missing"),
    ]
    assert report.active_count == 1
    assert report.inactive_count == 1
    assert report.missing_count == 1


def test_audit_playlist_preserves_empty_playlist() -> None:
    report = audit_playlist((), {})

    assert report.entries == ()
    assert report.active_count == 0
    assert report.inactive_count == 0
    assert report.missing_count == 0
