import pytest

from soundmind.recommendation.text_retrieval import CatalogTextRetrievalEngine
from soundmind.storage.models import TrackRow


def row(
    track_id: str,
    *,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    album_artist: str | None = None,
    composer: str | None = None,
    genre: str | None = None,
    file_name: str = "track.mp3",
    status: str = "active",
) -> TrackRow:
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=file_name,
        file_size=1,
        modified_at_ns=1,
        status=status,
        title=title,
        artist=artist,
        album=album,
        album_artist=album_artist,
        composer=composer,
        genre=genre,
    )


def test_search_ranks_title_match_before_lower_weight_fields() -> None:
    engine = CatalogTextRetrievalEngine()
    rows = [
        row("artist-match", artist="Hero"),
        row("title-match", title="Hero"),
        row("genre-match", genre="Hero"),
    ]

    results = engine.search("hero", rows)

    assert [item.track_id for item in results] == [
        "title-match",
        "artist-match",
        "genre-match",
    ]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(0.85)
    assert results[2].score == pytest.approx(0.6)


def test_search_scores_each_query_token_and_reports_matching_fields() -> None:
    engine = CatalogTextRetrievalEngine()
    rows = [
        row("full", title="Hero Entry", genre="action"),
        row("partial", title="Hero"),
        row("other", title="Romance"),
    ]

    results = engine.search("hero entry", rows)

    assert [item.track_id for item in results] == ["full", "partial"]
    assert results[0].score == pytest.approx(1.0)
    assert results[0].matched_fields == ("title",)
    assert results[1].score == pytest.approx(0.5)


def test_search_is_case_insensitive_and_excludes_inactive_rows() -> None:
    engine = CatalogTextRetrievalEngine()
    rows = [
        row("active", title="CINEMATIC Hero", status="active"),
        row("inactive", title="cinematic hero", status="missing"),
    ]

    results = engine.search("cinematic HERO", rows)

    assert [item.track_id for item in results] == ["active"]


def test_search_uses_stable_track_id_tiebreaker() -> None:
    engine = CatalogTextRetrievalEngine()
    rows = [row("b", title="Hero"), row("a", title="Hero")]

    assert [item.track_id for item in engine.search("hero", rows)] == ["a", "b"]


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [
        ("", 10, "query"),
        ("!!!", 10, "query"),
        ("hero", 0, "limit"),
    ],
)
def test_search_rejects_invalid_input(query: str, limit: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        CatalogTextRetrievalEngine().search(query, [], limit=limit)


def test_search_can_expand_music_domain_aliases_without_changing_default() -> None:
    engine = CatalogTextRetrievalEngine()
    rows = [
        row("bgm-title", title="Hero BGM"),
        row("background-music", title="Hero Background Music"),
    ]

    default_results = engine.search("score", rows)
    expanded_results = engine.search("score", rows, expand=True)

    assert default_results == []
    assert [item.track_id for item in expanded_results] == [
        "background-music",
        "bgm-title",
    ]
