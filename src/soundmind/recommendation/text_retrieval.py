"""Deterministic lexical retrieval over persisted catalog metadata."""

import re
from dataclasses import dataclass

from soundmind.storage.models import TrackRow

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)

_FIELD_WEIGHTS = (
    ("title", 1.0),
    ("artist", 0.85),
    ("album", 0.75),
    ("album_artist", 0.65),
    ("composer", 0.55),
    ("genre", 0.6),
    ("file_name", 0.3),
)


@dataclass(frozen=True)
class TextSearchResult:
    """A deterministic catalog text-match result."""

    track_id: str
    score: float
    matched_fields: tuple[str, ...]
    title: str | None = None
    artist: str | None = None
    album: str | None = None


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token.casefold() for token in _TOKEN_RE.findall(value)}


def _field_score(query_tokens: set[str], row: TrackRow) -> tuple[float, tuple[str, ...]]:
    if not query_tokens:
        return 0.0, ()

    matched_by_field: list[tuple[str, set[str]]] = []
    for field_name, _weight in _FIELD_WEIGHTS:
        values = _tokens(getattr(row, field_name))
        matched = query_tokens & values
        if matched:
            matched_by_field.append((field_name, matched))

    covered: set[str] = set()
    strongest_fields: list[str] = []
    for field_name, matched in matched_by_field:
        new_tokens = matched - covered
        if new_tokens:
            strongest_fields.append(field_name)
            covered.update(new_tokens)

    if not covered:
        return 0.0, ()

    token_weight = 0.0
    matched_weight = 0.0
    for token in query_tokens:
        weights = [
            weight
            for field_name, weight in _FIELD_WEIGHTS
            if token in _tokens(getattr(row, field_name))
        ]
        best_weight = max(weights, default=0.0)
        token_weight += best_weight
        if token in covered:
            matched_weight += best_weight

    score = matched_weight / token_weight if token_weight else 0.0
    return score, tuple(strongest_fields)


class CatalogTextRetrievalEngine:
    """Rank active catalog rows by deterministic lexical metadata overlap."""

    def search(
        self,
        query: str,
        rows: list[TrackRow],
        *,
        limit: int = 10,
    ) -> list[TextSearchResult]:
        if query is None or not query.strip():
            raise ValueError("query must be non-empty")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        query_tokens = _tokens(query)
        if not query_tokens:
            raise ValueError("query must contain searchable text")

        results: list[TextSearchResult] = []
        for row in rows:
            if row.status != "active":
                continue
            score, matched_fields = _field_score(query_tokens, row)
            if score <= 0:
                continue
            results.append(
                TextSearchResult(
                    track_id=row.track_id,
                    score=score,
                    matched_fields=matched_fields,
                    title=row.title,
                    artist=row.artist,
                    album=row.album,
                )
            )

        results.sort(key=lambda item: (-item.score, item.track_id))
        return results[:limit]
