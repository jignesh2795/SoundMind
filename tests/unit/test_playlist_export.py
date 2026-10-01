from datetime import UTC, datetime

from soundmind.playlist_export import saved_playlist_to_json
from soundmind.playlist_storage import SavedPlaylist
from soundmind.sequence import SequenceItem


def test_saved_playlist_to_json_is_deterministic() -> None:
    playlist = SavedPlaylist(
        name="Focus Music",
        items=(
            SequenceItem(track_id="a", sequence_score=0.9, base_score=0.8),
            SequenceItem(track_id="b", sequence_score=0.7, base_score=0.6),
        ),
        created_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 10, 1, 11, 0, tzinfo=UTC),
    )

    assert saved_playlist_to_json(playlist) == (
        "{\n"
        '  "version": 1,\n'
        '  "name": "Focus Music",\n'
        '  "created_at": "2026-10-01T10:00:00+00:00",\n'
        '  "updated_at": "2026-10-01T11:00:00+00:00",\n'
        '  "items": [\n'
        '    {\n'
        '      "position": 1,\n'
        '      "track_id": "a",\n'
        '      "sequence_score": 0.9,\n'
        '      "base_score": 0.8\n'
        '    },\n'
        '    {\n'
        '      "position": 2,\n'
        '      "track_id": "b",\n'
        '      "sequence_score": 0.7,\n'
        '      "base_score": 0.6\n'
        '    }\n'
        '  ]\n'
        "}\n"
    )
