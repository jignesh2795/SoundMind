import json

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


def _document(**overrides) -> str:
    document = {
        "version": 1,
        "name": "Focus Music",
        "created_at": "2026-10-01T10:00:00+00:00",
        "updated_at": "2026-10-01T11:00:00+00:00",
        "items": [],
    }
    document.update(overrides)
    return json.dumps(document)


def test_parse_playlist_json_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError, match="playlist must be an object"):
        parse_playlist_json("[]")


def test_parse_playlist_json_rejects_non_integer_versions() -> None:
    for version in (True, "1"):
        with pytest.raises(ValueError, match="version must be an integer"):
            parse_playlist_json(_document(version=version))


def test_parse_playlist_json_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        parse_playlist_json(_document(name="   "))


def test_parse_playlist_json_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="updated_at must be a valid ISO-8601 timestamp"):
        parse_playlist_json(_document(updated_at="not-a-timestamp"))


def test_parse_playlist_json_rejects_non_array_items() -> None:
    with pytest.raises(ValueError, match="items must be an array"):
        parse_playlist_json(_document(items={}))


def test_parse_playlist_json_rejects_non_object_items() -> None:
    with pytest.raises(ValueError, match="item must be an object"):
        parse_playlist_json(_document(items=[[]]))


def test_parse_playlist_json_rejects_non_integer_positions() -> None:
    item = {
        "track_id": "a",
        "sequence_score": 1,
        "base_score": 1,
    }
    for position in (True, "1"):
        with pytest.raises(ValueError, match="item position must be an integer"):
            parse_playlist_json(_document(items=[{**item, "position": position}]))


def test_parse_playlist_json_rejects_blank_track_ids() -> None:
    with pytest.raises(ValueError, match="track_id must be a non-empty string"):
        parse_playlist_json(
            _document(
                items=[
                    {
                        "position": 1,
                        "track_id": "   ",
                        "sequence_score": 1,
                        "base_score": 1,
                    }
                ]
            )
        )


def test_parse_playlist_json_rejects_non_numeric_scores() -> None:
    item = {
        "position": 1,
        "track_id": "a",
        "sequence_score": 1,
        "base_score": 1,
    }
    with pytest.raises(ValueError, match="sequence_score must be a number"):
        parse_playlist_json(_document(items=[{**item, "sequence_score": "0.5"}]))
    with pytest.raises(ValueError, match="base_score must be a number"):
        parse_playlist_json(_document(items=[{**item, "base_score": True}]))

def test_parse_playlist_json_rejects_non_finite_scores() -> None:
    item = {
        "position": 1,
        "track_id": "a",
        "sequence_score": 1,
        "base_score": 1,
    }
    with pytest.raises(ValueError, match="sequence_score must be finite"):
        parse_playlist_json(_document(items=[{**item, "sequence_score": float("nan")}]))
    with pytest.raises(ValueError, match="base_score must be finite"):
        parse_playlist_json(_document(items=[{**item, "base_score": float("inf")}]))
