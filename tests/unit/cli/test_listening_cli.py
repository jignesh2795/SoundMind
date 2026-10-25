from datetime import UTC, datetime
from pathlib import Path

import pytest

from soundmind.cli.main import build_parser, main
from soundmind.preferences.models import ListeningEvent, ListeningEventType


NOW = datetime(2026, 10, 25, 7, 0, tzinfo=UTC)


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def event(
    track_id: str = "track-a",
    event_type: ListeningEventType = ListeningEventType.LIKE,
    *,
    occurred_at: datetime = NOW,
    context: str | None = "Coding",
    seconds_played: float | None = 12.5,
) -> ListeningEvent:
    return ListeningEvent(track_id, event_type, occurred_at, context, seconds_played)


def test_event_parser_defaults_and_captures_options() -> None:
    parser = build_parser()
    args = parser.parse_args(["event", "list"])

    assert args.command == "event"
    assert args.event_command == "list"
    assert args.limit == 20
    assert args.db == Path("data/database/soundmind.db")

    add_defaults = parser.parse_args(["event", "add", "track-a", "like"])
    assert add_defaults.db == Path("data/database/soundmind.db")
    assert add_defaults.at is None
    assert add_defaults.context is None
    assert add_defaults.seconds_played is None

    args = parser.parse_args(
        [
            "event",
            "add",
            "track-a",
            "like",
            "--at",
            "2026-10-25T12:00:00+05:30",
            "--context",
            "coding",
            "--seconds-played",
            "42.5",
            "--db",
            "library.db",
        ]
    )

    assert args.event_command == "add"
    assert args.track_id == "track-a"
    assert args.event_type == "like"
    assert args.at == NOW
    assert args.context == "coding"
    assert args.seconds_played == 42.5
    assert args.db == Path("library.db")


def test_event_parser_rejects_invalid_type_and_naive_timestamp() -> None:
    with pytest.raises(SystemExit) as invalid_type:
        build_parser().parse_args(["event", "add", "track-a", "love"])
    assert invalid_type.value.code == 2

    with pytest.raises(SystemExit) as naive_time:
        build_parser().parse_args(
            ["event", "add", "track-a", "like", "--at", "2026-10-25T12:00:00"]
        )
    assert naive_time.value.code == 2


def test_event_add_dispatches_options_and_prints_record(monkeypatch, capsys) -> None:
    captured = {}

    def record(session, track_id, event_type, **kwargs):
        captured.update(
            session=session,
            track_id=track_id,
            event_type=event_type,
            **kwargs,
        )
        return event(
            track_id,
            ListeningEventType(event_type),
            occurred_at=kwargs["occurred_at"] or NOW,
            context=kwargs["context"],
            seconds_played=kwargs["seconds_played"],
        )

    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: (lambda: FakeSession()),
    )
    monkeypatch.setattr("soundmind.cli.main.record_listening_event", record)

    assert main(
        [
            "event",
            "add",
            "track-a",
            "like",
            "--at",
            NOW.isoformat(),
            "--context",
            "coding",
            "--seconds-played",
            "12.5",
            "--db",
            "library.db",
        ]
    ) == 0

    assert captured["track_id"] == "track-a"
    assert captured["event_type"] == "like"
    assert captured["occurred_at"] == NOW
    assert captured["context"] == "coding"
    assert captured["seconds_played"] == 12.5
    assert capsys.readouterr().out == (
        "Recorded: 2026-10-25T07:00:00+00:00\tlike\ttrack-a\tcoding\t12.5\n"
    )


def test_event_list_dispatches_limit_and_prints_stable_columns(monkeypatch, capsys) -> None:
    captured = {}

    def list_events(session, *, limit):
        captured["session"] = session
        captured["limit"] = limit
        return [
            event(),
            event(
                "track-b",
                ListeningEventType.SKIP,
                context=None,
                seconds_played=None,
            ),
        ]

    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: (lambda: FakeSession()),
    )
    monkeypatch.setattr("soundmind.cli.main.list_listening_events", list_events)

    assert main(["event", "list", "--limit", "7", "--db", "events.db"]) == 0

    assert captured["limit"] == 7
    assert capsys.readouterr().out == (
        "2026-10-25T07:00:00+00:00\tlike\ttrack-a\tCoding\t12.5\n"
        "2026-10-25T07:00:00+00:00\tskip\ttrack-b\t\t\n"
    )


def test_event_list_empty_output_is_explicit(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: (lambda: FakeSession()),
    )
    monkeypatch.setattr("soundmind.cli.main.list_listening_events", lambda session, *, limit: [])

    assert main(["event", "list"]) == 0
    assert capsys.readouterr().out == "No listening events.\n"

def test_event_list_escapes_context_delimiters(monkeypatch, capsys) -> None:
    context = "line one\tline two\rline three\nline four"
    monkeypatch.setattr(
        "soundmind.cli.main.create_session_factory",
        lambda path: (lambda: FakeSession()),
    )
    monkeypatch.setattr(
        "soundmind.cli.main.list_listening_events",
        lambda session, *, limit: [event(context=context)],
    )

    assert main(["event", "list"]) == 0
    output = capsys.readouterr().out
    assert output.count("\n") == 1
    assert r"line one\tline two\rline three\nline four" in output