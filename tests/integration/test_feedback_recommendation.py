"""End-to-end regression tests for captured feedback reaching recommendations."""

import re
from datetime import UTC, datetime

from soundmind.cli.main import main
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow

NOW = datetime(2026, 10, 25, 7, 0, tzinfo=UTC)


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
        title="Cinematic Track",
        genre="cinematic",
        rms_energy=0.5,
        tempo_bpm=100.0,
    )


def _record_feedback(db, track_id: str, context: str, capsys) -> None:
    assert (
        main(
            [
                "event",
                "add",
                track_id,
                "like",
                "--at",
                NOW.isoformat(),
                "--context",
                context,
                "--db",
                str(db),
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.startswith("Recorded: ")


def _recommend(db, context: str, capsys) -> tuple[tuple[str, ...], str]:
    assert (
        main(
            [
                "recommend",
                "cinematic BGM",
                "--context",
                context,
                "--now",
                NOW.isoformat(),
                "--limit",
                "2",
                "--explain",
                "--db",
                str(db),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    ranked_section = output.split("Ranked:\n", maxsplit=1)[1].split(
        "Playlist:\n", maxsplit=1
    )[0]
    order = tuple(
        match.group(1)
        for line in ranked_section.splitlines()
        if (match := re.match(r"^\d+\. ([^\t]+)\t", line))
    )
    return order, output


def test_cli_feedback_reaches_recommendation_and_stays_contextual(
    tmp_path, capsys
) -> None:
    db = tmp_path / "soundmind.db"
    factory = create_session_factory(db)
    with factory() as session:
        session.add_all([track("coding-favorite"), track("gym-favorite")])
        session.commit()

    # Capture feedback exclusively through the public CLI, into the same SQLite
    # database later read by the public recommendation command.
    _record_feedback(db, "coding-favorite", "coding", capsys)
    _record_feedback(db, "gym-favorite", "gym", capsys)

    coding_order, coding_output = _recommend(db, "coding", capsys)
    repeated_coding_order, repeated_coding_output = _recommend(db, "coding", capsys)
    gym_order, gym_output = _recommend(db, "gym", capsys)

    assert coding_order == ("coding-favorite", "gym-favorite")
    assert gym_order == ("gym-favorite", "coding-favorite")
    assert repeated_coding_order == coding_order
    assert repeated_coding_output == coding_output

    # The explain output proves the captured event reaches the existing
    # preference signal and that the default M1 preference weight is unchanged.
    assert "preference: raw=0.462117 weight=0.180000" in coding_output
    assert "preference: raw=0.000000 weight=0.180000" in coding_output
    assert "preference: raw=0.462117 weight=0.180000" in gym_output
