from soundmind.recommendation.query_expansion import expand_query


def test_expand_query_preserves_original_and_adds_bgm_aliases():
    assert expand_query("hero bgm") == (
        "hero bgm",
        "hero background music",
        "hero background score",
    )


def test_expand_query_supports_phrase_aliases():
    assert expand_query("cinematic background score") == (
        "cinematic background score",
        "cinematic background music",
        "cinematic bgm",
    )


def test_expand_query_is_case_insensitive_and_deduplicated():
    assert expand_query("Hero BGM") == (
        "Hero BGM",
        "Hero background music",
        "Hero background score",
    )


def test_expand_query_without_known_terms_returns_original():
    assert expand_query("hero entry") == ("hero entry",)
