import math

import pytest

from soundmind.evaluation import (
    build_frozen_pool,
    check_evaluability,
    dcg_at_10,
    evaluate_query,
    gain,
    idcg_at_10,
    mrr_at_10,
    recall_at_10,
)


def test_gain_uses_exponential_relevance_scale() -> None:
    assert [gain(grade) for grade in range(4)] == [0, 1, 3, 7]


@pytest.mark.parametrize("grade", [-1, 4, True, 1.0])
def test_gain_rejects_invalid_grade(grade) -> None:
    with pytest.raises(ValueError):
        gain(grade)


def test_ndcg_is_one_for_ideal_order_and_lower_when_reversed() -> None:
    pool = ["a", "b", "c"]
    grades = {"a": 3, "b": 2, "c": 0}
    assert dcg_at_10(["a", "b", "c"], grades) == pytest.approx(
        idcg_at_10(pool, grades)
    )
    ideal = idcg_at_10(pool, grades)
    reversed_dcg = dcg_at_10(["c", "b", "a"], grades)
    assert reversed_dcg / ideal < 1.0


def test_dcg_preserves_position_of_unjudged_result() -> None:
    dcg = dcg_at_10(["unjudged", "strong"], {"strong": 3})
    assert dcg == pytest.approx(7 / math.log2(3))
    assert dcg < 7


def test_pool_smaller_than_ten_has_no_padding() -> None:
    pool = ["a", "b", "c"]
    grades = {"a": 3, "b": 2, "c": 1}
    expected = 7 + 3 / math.log2(3) + 1 / math.log2(4)
    assert idcg_at_10(pool, grades) == pytest.approx(expected)


def test_pooled_recall_and_mrr_use_grade_two_threshold() -> None:
    pool = ["a", "b", "c"]
    grades = {"a": 3, "b": 2, "c": 1}
    assert recall_at_10(["c", "b"], pool, grades) == pytest.approx(0.5)
    assert mrr_at_10(["c", "b", "a"], grades) == pytest.approx(0.5)
    assert mrr_at_10(["c"], grades) == 0.0


def test_empty_results_score_zero_when_pool_is_evaluable() -> None:
    result = evaluate_query(["a", "b", "c"], {"a": 3, "b": 2, "c": 0}, [])
    assert result["status"] == "evaluable"
    assert result["metrics"] == {"nDCG@10": 0.0, "Recall@10": 0.0, "MRR@10": 0.0}


def test_valid_complete_pool_is_evaluable() -> None:
    ok, reasons = check_evaluability(
        ["a", "b", "c"], {"a": 3, "b": 2, "c": 0}, ["a", "b", "c"]
    )
    assert ok
    assert reasons == []


def test_incomplete_pool_makes_all_metrics_not_evaluable() -> None:
    result = evaluate_query(["a", "b", "c"], {"a": 3, "b": 2}, ["a", "b"])
    assert result["status"] == "not_evaluable"
    assert any("1 of 3 pooled tracks unjudged" in r for r in result["reasons"])
    assert result["metrics"] == {"nDCG@10": None, "Recall@10": None, "MRR@10": None}


def test_track_outside_pool_fails_shared_gate() -> None:
    ok, reasons = check_evaluability(
        ["a", "b", "c"], {"a": 3, "b": 2, "c": 0}, ["a", "b", "outside"]
    )
    assert not ok
    assert "pool: returned tracks outside frozen pool" in reasons


def test_pool_with_fewer_than_three_judgments_is_not_evaluable() -> None:
    ok, reasons = check_evaluability(["a", "b"], {"a": 3, "b": 0}, ["a", "b"])
    assert not ok
    assert any("pool too small" in r for r in reasons)


def test_zero_relevant_pool_and_zero_idcg_are_not_evaluable() -> None:
    ok, reasons = check_evaluability(["a", "b", "c"], {"a": 0, "b": 1, "c": 0}, ["a"])
    assert not ok
    assert "no judged-relevant tracks in frozen pool" in reasons
    assert "IDCG@10 = 0: all judged grades are 0" in reasons


def test_all_unjudged_pool_fails_and_does_not_become_grade_zero() -> None:
    result = evaluate_query(["a", "b", "c"], {}, ["a", "b", "c"])
    assert result["status"] == "not_evaluable"
    assert result["metrics"] == {"nDCG@10": None, "Recall@10": None, "MRR@10": None}


def test_frozen_pool_is_distinct_union_with_ordered_provenance() -> None:
    manifest = build_frozen_pool(
        {"catalog": ["a", "b"], "lexical": ["b", "c"]},
        {"catalog": 10, "lexical": 10},
        dataset_version="1.0.0",
    )
    assert set(manifest["members"]) == {"a", "b", "c"}
    assert manifest["ordered_top10_by_mode"]["catalog"] == ["a", "b"]
    assert manifest["ordered_top10_by_mode"]["lexical"] == ["b", "c"]
