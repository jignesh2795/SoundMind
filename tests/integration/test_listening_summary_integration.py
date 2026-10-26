from datetime import UTC, datetime

import pytest

from soundmind.cli.main import main
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow

NOW = datetime(2026, 10, 26, 7, 0, tzinfo=UTC)


def track(track_id: str) -> TrackRow:
    return TrackRow(
        track_id=track_id,
        content_hash=(track_id + "x" * 64)[:64],
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=100,
        modified_at_ns=1,
        status="active",
        created_at=NOW,
        updated_at=NOW,
        title=f"Track {track_id}",
    )


def test_cli_summary_aggregates_persisted_events_by_type_and_context(
    tmp_path, capsys
) -> None:
    db = tmp_path / "soundmind.db"
    factory = create_session_factory(db)
    with factory() as session:
        session.add_all([track("coding-track"), track("workout-track")])
        session.commit()

    assert (
        main(
            [
                "event",
                "add",
                "coding-track",
                "like",
                "--at",
                NOW.isoformat(),
                "--context",
                "Coding",
                "--db",
                str(db),
            ]
        )
        == 0
    )
    capsys.readouterr()

    later = datetime(2026, 10, 26, 8, 0, tzinfo=UTC)
    assert (
        main(
            [
                "event",
                "add",
                "workout-track",
                "skip",
                "--at",
                later.isoformat(),
                "--context",
                "Workout",
                "--seconds-played",
                "8.5",
                "--db",
                str(db),
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["event", "summary", "--limit", "10", "--db", str(db)]) == 0
    assert capsys.readouterr().out == (
        "Listening summary (most recent 10 events)\n"
        "Events: 2\n"
        "Distinct tracks: 2\n"
        "By event type:\n"
        "  play: 0\n"
        "  complete: 0\n"
        "  skip: 1\n"
        "  like: 1\n"
        "  dislike: 0\n"
        "  replay: 0\n"
        "By context:\n"
        "  coding: 1 event, 1 track\n"
        "  workout: 1 event, 1 track\n"
    )

    assert main(["event", "summary", "--limit", "1", "--db", str(db)]) == 0
    assert capsys.readouterr().out == (
        "Listening summary (most recent 1 event)\n"
        "Events: 1\n"
        "Distinct tracks: 1\n"
        "By event type:\n"
        "  play: 0\n"
        "  complete: 0\n"
        "  skip: 1\n"
        "  like: 0\n"
        "  dislike: 0\n"
        "  replay: 0\n"
        "By context:\n"
        "  workout: 1 event, 1 track\n"
    )


def test_cli_summary_empty_history_is_explicit(tmp_path, capsys) -> None:
    db = tmp_path / "empty.db"

    assert main(["event", "summary", "--db", str(db)]) == 0
    assert capsys.readouterr().out == (
        "Listening summary (most recent 1000 events)\n"
        "Events: 0\n"
        "Distinct tracks: 0\n"
        "By event type:\n"
        "  play: 0\n"
        "  complete: 0\n"
        "  skip: 0\n"
        "  like: 0\n"
        "  dislike: 0\n"
        "  replay: 0\n"
        "By context:\n"
        "  (none)\n"
    )

def test_cli_summary_rejects_non_positive_limit(tmp_path) -> None:
    db = tmp_path / "events.db"

    with pytest.raises(ValueError, match="limit must be positive"):
        main(["event", "summary", "--limit", "0", "--db", str(db)])
