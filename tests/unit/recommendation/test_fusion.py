import pytest

from soundmind.recommendation.fusion import (
    CandidateSignals,
    FusionWeights,
    fuse_score,
    rank_candidates,
)


def test_weights_are_normalized():
    w=FusionWeights(2,2,4,1,1,0).normalized()
    assert w.learned==pytest.approx(.4); assert sum(vars(w).values())==pytest.approx(1)
def test_preference_signal_is_fused():
    c=CandidateSignals("a",learned_score=.5,preference_score=1)
    assert fuse_score(c,FusionWeights())==pytest.approx(.36)
def test_deterministic_tie():
    r=rank_candidates([CandidateSignals("b",learned_score=.8),CandidateSignals("a",learned_score=.8)],limit=2)
    assert [x.track_id for x in r]==["a","b"]
