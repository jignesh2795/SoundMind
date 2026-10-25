from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from soundmind.listening import list_listening_events, record_listening_event
from soundmind.preferences.models import ListeningEventType


class FakeSession:
    def __init__(self, *, exists: bool = True) -> None:
        self.exists = exists
        self.lookups: list[str] = []
        self.rows: list[object] = []
        self.commits = 0

    def get(self, model, track_id: str):
        self.lookups.append(track_id)
        if self.exists and track_id == "inactive-track":
            return SimpleNamespace(track_id=track_id, status="inactive")
        return None

    def add(self, row) -> None:
        self.rows.append(row)

    def commit(self) -> None:
        self.commits += 1


def test_record_accepts_existing_inactive_track_and_normalizes_timestamp() -> None:
    session = FakeSession()
    at = datetime(2026, 10, 25, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    event = record_listening_event(
        session,
        "inactive-track",
        "like",
        occurred_at=at,
        context="  Coding  ",
        seconds_played=12.5,
    )

    assert event.track_id == "inactive-track"
    assert event.event_type is ListeningEventType.LIKE
    assert event.occurred_at == datetime(2026, 10, 25, 6, 30, tzinfo=UTC)
    assert event.occurred_at.tzinfo is UTC
    assert event.context == "  Coding  "
    assert event.seconds_played == 12.5
    assert len(session.rows) == 1
    assert session.rows[0].event_type == "like"
    assert session.commits == 1


@pytest.mark.parametrize("track_id", ["", "missing-track"])
def test_record_rejects_empty_or_unknown_track_id(track_id: str) -> None:
    session = FakeSession(exists=False)

    with pytest.raises(KeyError, match="Track not found"):
        record_listening_event(session, track_id, ListeningEventType.LIKE)

    assert session.rows == []
    assert session.commits == 0


def test_record_rejects_naive_timestamp() -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="timezone"):
        record_listening_event(
            session,
            "inactive-track",
            ListeningEventType.LIKE,
            occurred_at=datetime(2026, 10, 25, 12, 0),  # noqa: DTZ001 -- deliberately naive to test rejection
        )

    assert session.rows == []


@pytest.mark.parametrize("seconds_played", [-1.0, float("inf"), float("-inf"), float("nan"), True])
def test_record_rejects_invalid_seconds_played(seconds_played: float) -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="seconds_played"):
        record_listening_event(
            session,
            "inactive-track",
            ListeningEventType.PLAY,
            seconds_played=seconds_played,
        )

    assert session.rows == []


def test_record_normalizes_whitespace_only_context_to_none() -> None:
    event = record_listening_event(
        FakeSession(),
        "inactive-track",
        ListeningEventType.SKIP,
        context=" \t  ",
    )

    assert event.context is None


def test_record_defaults_to_utc_now() -> None:
    event = record_listening_event(
        FakeSession(),
        "inactive-track",
        ListeningEventType.PLAY,
    )

    assert event.occurred_at.tzinfo is UTC
    assert abs((datetime.now(UTC) - event.occurred_at).total_seconds()) < 5


def test_record_rejects_unknown_event_type() -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="event type"):
        record_listening_event(session, "inactive-track", "love")

    assert session.rows == []


def test_list_forwards_limit(monkeypatch) -> None:
    captured = {}

    class FakeRepository:
        def __init__(self, session) -> None:
            captured["session"] = session

        def list_recent(self, *, limit):
            captured["limit"] = limit
            return ["event"]

    monkeypatch.setattr("soundmind.listening.ListeningEventRepository", FakeRepository)
    session = object()

    assert list_listening_events(session, limit=37) == ["event"]
    assert captured == {"session": session, "limit": 37}


def test_list_reuses_repository_positive_limit_validation() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        list_listening_events(FakeSession(), limit=0)
