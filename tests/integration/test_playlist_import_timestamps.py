import json
from datetime import UTC, datetime

from soundmind.cli.main import main
from soundmind.playlist_storage import PlaylistRepository
from soundmind.storage.database import create_session_factory


def test_json_import_uses_destination_timestamps_not_source_timestamps(tmp_path) -> None:
    source = tmp_path / "source.json"
    database = tmp_path / "soundmind.db"
    source_created = datetime(2000, 1, 1, 10, 0, tzinfo=UTC)
    source_updated = datetime(2000, 1, 1, 11, 0, tzinfo=UTC)
    source.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "Focus Music",
                "created_at": source_created.isoformat(),
                "updated_at": source_updated.isoformat(),
                "items": [
                    {
                        "position": 1,
                        "track_id": "track-a",
                        "sequence_score": 0.9,
                        "base_score": 0.8,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["playlist", "import", str(source), "--db", str(database)]) == 0

    session_factory = create_session_factory(database)
    with session_factory() as session:
        saved = PlaylistRepository(session).get("Focus Music")

    assert saved is not None
    assert saved.created_at != source_created
    assert saved.updated_at != source_updated
    assert saved.created_at == saved.updated_at
    assert saved.items[0].track_id == "track-a"
