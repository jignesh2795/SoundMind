import pytest

from soundmind.recommendation.hybrid_retrieval import (
    HybridSearchResult,
    HybridWeights,
    fuse_search_results,
    normalize_scores,
)
from soundmind.recommendation.semantic_text_retrieval import SemanticTextSearchResult
from soundmind.recommendation.text_retrieval import TextSearchResult


def lexical(track_id: str, score: float) -> TextSearchResult:
    return TextSearchResult(
        track_id=track_id,
        score=score,
        matched_fields=("title",),
        title=f"Title {track_id}",
        artist="Composer",
        album=None,
    )


def semantic(track_id: str, score: float) -> SemanticTextSearchResult:
    return SemanticTextSearchResult(
        track_id=track_id,
        score=score,
        title=f"Title {track_id}",
        artist="Composer",
        album=None,
    )


def test_weights_must_sum_positive_and_reject_negatives() -> None:
    assert HybridWeights(2.0, 2.0).normalized() == HybridWeights(0.5, 0.5)
    with pytest.raises(ValueError):
        HybridWeights(-0.5, 0.5)
    with pytest.raises(ValueError):
        HybridWeights(0.0, 0.0)


def test_normalize_scores_is_min_max() -> None:
    assert normalize_scores({}) == {}
    assert normalize_scores({"a": 0.8}) == {"a": 1.0}
    assert normalize_scores({"a": 0.8, "b": 0.8}) == {"a": 1.0, "b": 1.0}
    assert normalize_scores({"a": 1.0, "b": 0.5, "c": 0.0}) == pytest.approx(
        {"a": 1.0, "b": 0.5, "c": 0.0}
    )


def test_fusion_averages_both_sources_by_default() -> None:
    fused = fuse_search_results(
        [lexical("a", 1.0), lexical("b", 0.0)],
        [semantic("a", 0.0), semantic("b", 1.0)],
    )

    assert [(item.track_id, item.score) for item in fused] == [
        ("a", pytest.approx(0.5)),
        ("b", pytest.approx(0.5)),
    ]
    assert fused[0].lexical_score == pytest.approx(1.0)
    assert fused[0].semantic_score == pytest.approx(0.0)


def test_fusion_weights_shift_ranking() -> None:
    ranked = fuse_search_results(
        [lexical("a", 1.0), lexical("b", 0.0)],
        [semantic("a", -1.0), semantic("b", 1.0)],
        weights=HybridWeights(lexical=0.0, semantic=1.0),
    )

    assert [item.track_id for item in ranked] == ["b", "a"]


def test_union_keeps_single_source_candidates() -> None:
    fused = fuse_search_results([lexical("lex-only", 0.7)], [semantic("sem-only", 0.4)])

    assert {item.track_id for item in fused} == {"lex-only", "sem-only"}
    lex_only = next(item for item in fused if item.track_id == "lex-only")
    sem_only = next(item for item in fused if item.track_id == "sem-only")
    assert lex_only.semantic_score == 0.0
    assert sem_only.lexical_score == 0.0


def test_tie_breaking_is_deterministic_by_track_id() -> None:
    first = fuse_search_results([lexical("b", 0.5)], [semantic("a", 0.5)])
    second = fuse_search_results([lexical("b", 0.5)], [semantic("a", 0.5)])

    assert first == second
    assert [item.track_id for item in first] == ["a", "b"]


def test_empty_sources_return_empty_tuple() -> None:
    assert fuse_search_results([], []) == ()


def test_limit_truncates_fused_results() -> None:
    fused = fuse_search_results(
        [lexical("a", 1.0), lexical("b", 0.9), lexical("c", 0.1)],
        [],
        limit=2,
    )

    assert [item.track_id for item in fused] == ["a", "b"]


def test_duplicate_candidate_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate track_id"):
        fuse_search_results([lexical("a", 1.0), lexical("a", 0.5)], [])
    with pytest.raises(ValueError, match="duplicate track_id"):
        fuse_search_results([], [semantic("a", 0.5), semantic("a", 0.5)])


def test_invalid_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        fuse_search_results([lexical("a", 1.0)], [], limit=0)


def test_metadata_prefers_lexical_evidence() -> None:
    fused = fuse_search_results([lexical("a", 0.5)], [semantic("a", 0.5)])

    assert isinstance(fused[0], HybridSearchResult)
    assert fused[0].title == "Title a"
