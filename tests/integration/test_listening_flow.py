from datetime import UTC, datetime

import pytest

from soundmind.cli.main import main
from soundmind.preferences.contextual import ContextualPreferenceScorer
from soundmind.preferences.models import ListeningEventType
from soundmind.preferences.repository import ListeningEventRepository
from soundmind.preferences.scorer import PreferenceScorer
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


NOW = datetime(2026, 10, 25, 7, 0, tzinfo=UTC)


def track(track_id: str, *, status: str = "active") -> TrackRow:
    return TrackRow(
        track_id=track_id,
        content_hash=(track_id + "x" * 64)[:64],
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=100,
        modified_at_ns=1,
        status=status,
        created_at=NOW,
        updated_at=NOW,
        title=f"Track {track_id}",
    )


def test_cli_capture_round_trips_and_feeds_existing_preference_scorers(tmp_path, capsys) -> None:
    db = tmp_path / "soundmind.db"
    factory = create_session_factory(db)

    with factory() as session:
        session.add_all([track("inactive-track", status="inactive"), track("other-track")])
        session.commit()

    assert main(
        [
            "event",
            "add",
            "inactive-track",
            "like",
            "--at",
            NOW.isoformat(),
            "--context",
            "Coding",
            "--seconds-played",
            "42.0",
            "--db",
            str(db),
        ]
    ) == 0
    assert capsys.readouterr().out == (
        "Recorded: 2026-10-25T07:00:00+00:00\tlike\tinactive-track\tCoding\t42.0\n"
    )

    assert main(["event", "list", "--limit", "10", "--db", str(db)]) == 0
    assert capsys.readouterr().out == (
        "2026-10-25T07:00:00+00:00\tlike\tinactive-track\tCoding\t42.0\n"
    )

    with factory() as session:
        events = ListeningEventRepository(session).list_recent(limit=10)

    global_scores = PreferenceScorer().score_events(events, now=NOW)
    context_scores = ContextualPreferenceScorer().score_events(
        events,
        context=" coding ",
        now=NOW,
    )
    assert global_scores["inactive-track"] == pytest.approx(0.46211715726000974)
    assert context_scores["inactive-track"] == pytest.approx(0.46211715726000974)
    assert ListeningEventType.LIKE is events[0].event_type


def test_cli_capture_rejects_missing_track_without_persisting_event(tmp_path) -> None:
    db = tmp_path / "soundmind.db"
    factory = create_session_factory(db)

    with factory() as session:
        session.add(track("known-track"))
        session.commit()

    with pytest.raises(KeyError, match="Track not found"):
        main(["event", "add", "missing-track", "like", "--db", str(db)])

    with factory() as session:
        assert ListeningEventRepository(session).list_recent() == []
