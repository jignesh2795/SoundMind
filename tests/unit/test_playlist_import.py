import pytest

from soundmind.playlist_import import parse_playlist_json

VALID = """{
  "version": 1,
  "name": "Focus Music",
  "created_at": "2026-10-01T10:00:00+00:00",
  "updated_at": "2026-10-01T11:00:00+00:00",
  "items": [
    {
      "position": 1,
      "track_id": "a",
      "sequence_score": 0.9,
      "base_score": 0.8
    }
  ]
}
"""


def test_parse_playlist_json_preserves_order_and_scores() -> None:
    imported = parse_playlist_json(VALID)
    assert imported.name == "Focus Music"
    assert [
        (item.track_id, item.sequence_score, item.base_score)
        for item in imported.items
    ] == [("a", 0.9, 0.8)]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('{"version": 2, "name": "Focus", "created_at": "2026-10-01T10:00:00+00:00", "updated_at": "2026-10-01T10:00:00+00:00", "items": []}', "unsupported playlist JSON version"),
        ('{"version": 1, "name": "Focus", "created_at": "2026-10-01T10:00:00", "updated_at": "2026-10-01T10:00:00+00:00", "items": []}', "created_at must include a timezone"),
        ('{"version": 1, "name": "Focus", "created_at": "2026-10-01T10:00:00+00:00", "updated_at": "2026-10-01T10:00:00+00:00", "items": [{"position": 2, "track_id": "a", "sequence_score": 1, "base_score": 1}]}', "consecutive"),
        ('{"version": 1, "name": "Focus", "created_at": "2026-10-01T10:00:00+00:00", "updated_at": "2026-10-01T10:00:00+00:00", "items": [{"position": 1, "track_id": "a", "sequence_score": 1, "base_score": 1}, {"position": 2, "track_id": "a", "sequence_score": 0, "base_score": 0}]}', "duplicate track_id"),
    ],
)
def test_parse_playlist_json_rejects_invalid_documents(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_playlist_json(text)
