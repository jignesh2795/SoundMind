"""Hybrid lexical + semantic retrieval fusion (M12.4).

M12.4 is a retrieval-layer milestone only: it fuses the existing M12.1
lexical scores with M12.2/M12.3 semantic scores. It does not change
personal ranking, sequencing, or any fusion weights outside retrieval.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class HybridWeights:
    """Explicit fusion weights; normalized so they sum to 1."""

    lexical: float = 0.5
    semantic: float = 0.5

    def __post_init__(self) -> None:
        for name in ("lexical", "semantic"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(  # noqa: TRY004
                    f"{name} weight must be numeric"
                )
            if not math.isfinite(value):
                raise ValueError(f"{name} weight must be finite")
            if value < 0:
                raise ValueError(f"{name} weight must be non-negative")
        if self.lexical + self.semantic <= 0:
            raise ValueError("at least one fusion weight must be positive")

    def normalized(self) -> "HybridWeights":
        total = self.lexical + self.semantic
        return HybridWeights(self.lexical / total, self.semantic / total)


@dataclass(frozen=True)
class HybridSearchResult:
    """A unified hybrid retrieval result with both raw source scores."""

    track_id: str
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    lexical_normalized_score: float = 0.0
    semantic_normalized_score: float = 0.0
    lexical_contribution: float = 0.0
    semantic_contribution: float = 0.0
    title: str | None = None
    artist: str | None = None
    album: str | None = None


def _finite_score(value: float, *, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(  # noqa: TRY004
            f"{source} scores must be numeric"
        )
    if not math.isfinite(value):
        raise ValueError(f"{source} scores must be finite")
    return float(value)


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalize one source's scores into [0, 1].

    A source with no scores contributes nothing; a source whose scores
    are all equal maps every candidate to 1.0 (each is the best of its
    source). Missing candidates are handled by the caller as 0.0.
    """
    if not scores:
        return {}
    high = max(scores.values())
    low = min(scores.values())
    if high == low:
        return dict.fromkeys(scores, 1.0)
    span = high - low
    return {track_id: (score - low) / span for track_id, score in scores.items()}


def _collect(results: Sequence, *, source: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for result in results:
        if result.track_id in scores:
            raise ValueError(f"duplicate track_id: {result.track_id!r}")
        scores[result.track_id] = _finite_score(result.score, source=source)
    return scores


def _metadata(
    lexical_results: Sequence, semantic_results: Sequence
) -> dict[str, tuple[str | None, str | None, str | None]]:
    metadata: dict[str, tuple[str | None, str | None, str | None]] = {}
    for result in semantic_results:
        metadata[result.track_id] = (result.title, result.artist, result.album)
    for result in lexical_results:
        metadata[result.track_id] = (result.title, result.artist, result.album)
    return metadata


def fuse_search_results(
    lexical_results: Sequence,
    semantic_results: Sequence,
    *,
    weights: HybridWeights | None = None,
    limit: int = 10,
) -> tuple[HybridSearchResult, ...]:
    """Fuse lexical and semantic result lists into a deterministic union.

    hybrid = lexical_weight * normalized_lexical
           + semantic_weight * normalized_semantic

    Candidates present in only one source score 0.0 on the other.
    Ordering is (-hybrid_score, track_id); at most ``limit`` items.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    effective = (weights or HybridWeights()).normalized()

    lexical_scores = _collect(lexical_results, source="lexical")
    semantic_scores = _collect(semantic_results, source="semantic")
    if not lexical_scores and not semantic_scores:
        return ()

    normalized_lexical = normalize_scores(lexical_scores)
    normalized_semantic = normalize_scores(semantic_scores)
    metadata = _metadata(lexical_results, semantic_results)

    fused = [
        HybridSearchResult(
            track_id=track_id,
            score=effective.lexical * normalized_lexical.get(track_id, 0.0)
            + effective.semantic * normalized_semantic.get(track_id, 0.0),
            lexical_score=lexical_scores.get(track_id, 0.0),
            semantic_score=semantic_scores.get(track_id, 0.0),
            lexical_normalized_score=normalized_lexical.get(track_id, 0.0),
            semantic_normalized_score=normalized_semantic.get(track_id, 0.0),
            lexical_contribution=effective.lexical
            * normalized_lexical.get(track_id, 0.0),
            semantic_contribution=effective.semantic
            * normalized_semantic.get(track_id, 0.0),
            title=metadata[track_id][0],
            artist=metadata[track_id][1],
            album=metadata[track_id][2],
        )
        for track_id in set(lexical_scores) | set(semantic_scores)
    ]
    fused.sort(key=lambda item: (-item.score, item.track_id))
    return tuple(fused[:limit])
