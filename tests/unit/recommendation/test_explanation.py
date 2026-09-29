from soundmind.recommendation.fusion import CandidateSignals, FusionWeights, explain_candidate


def test_explanation_matches_fused_score():
    candidate = CandidateSignals("a", metadata_score=.2, learned_score=.8, preference_score=.5)
    explanation = explain_candidate(candidate, FusionWeights())
    assert explanation.total_score == sum(x.contribution for x in explanation.contributions)
    assert explanation.strongest_signal == "learned"

def test_non_finite_signal_is_safe():
    import math
    explanation = explain_candidate(CandidateSignals("a", metadata_score=math.nan), FusionWeights())
    assert explanation.total_score == 0.0
