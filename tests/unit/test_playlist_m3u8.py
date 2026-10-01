from soundmind.playlist_m3u8 import M3U8Track, saved_playlist_to_m3u8
from soundmind.sequence import SequenceItem


def test_saved_playlist_to_m3u8_is_deterministic() -> None:
    items = (
        SequenceItem(track_id="a", sequence_score=0.9, base_score=0.8),
        SequenceItem(track_id="b", sequence_score=0.7, base_score=0.6),
    )
    tracks = {
        "a": M3U8Track(
            source_uri="file:///music/hero%20theme.mp3",
            title="Hero Theme",
            artist="Composer A",
            duration_seconds=123.4,
        ),
        "b": M3U8Track(
            source_uri="file:///music/night.mp3",
            title="Night",
            artist=None,
            duration_seconds=None,
        ),
    }

    assert saved_playlist_to_m3u8(items, tracks) == (
        "#EXTM3U\n"
        "#EXTINF:123,Hero Theme — Composer A\n"
        "file:///music/hero%20theme.mp3\n"
        "#EXTINF:-1,Night\n"
        "file:///music/night.mp3\n"
    )


def test_saved_playlist_to_m3u8_falls_back_to_track_id() -> None:
    item = SequenceItem(track_id="track-a", sequence_score=0.0, base_score=0.0)
    tracks = {
        "track-a": M3U8Track(
            source_uri="file:///music/a.mp3",
            title=None,
            artist=None,
        )
    }

    assert saved_playlist_to_m3u8((item,), tracks) == (
        "#EXTM3U\n"
        "#EXTINF:-1,track-a\n"
        "file:///music/a.mp3\n"
    )


def test_saved_playlist_to_m3u8_rejects_missing_catalog_track() -> None:
    item = SequenceItem(track_id="missing", sequence_score=0.0, base_score=0.0)

    try:
        saved_playlist_to_m3u8((item,), {})
    except ValueError as exc:
        assert str(exc) == "track not found in catalog: 'missing'"
    else:
        raise AssertionError("expected ValueError")


def test_saved_playlist_to_m3u8_rejects_non_file_source() -> None:
    item = SequenceItem(track_id="remote", sequence_score=0.0, base_score=0.0)
    tracks = {
        "remote": M3U8Track(source_uri="https://example.com/track.mp3")
    }

    try:
        saved_playlist_to_m3u8((item,), tracks)
    except ValueError as exc:
        assert str(exc) == "track source is not a local file URI: 'remote'"
    else:
        raise AssertionError("expected ValueError")


def test_saved_playlist_to_m3u8_handles_empty_playlist() -> None:
    assert saved_playlist_to_m3u8((), {}) == "#EXTM3U\n"
