"""Deterministic lexical retrieval over persisted catalog metadata."""

import re
from dataclasses import dataclass

from soundmind.recommendation.query_expansion import expand_query
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
    field_tokens = {
        field_name: _tokens(getattr(row, field_name))
        for field_name, _weight in _FIELD_WEIGHTS
    }
    for field_name, _weight in _FIELD_WEIGHTS:
        matched = query_tokens & field_tokens[field_name]
        if matched:
            matched_by_field.append((field_name, matched))

    covered: set[str] = set()
    matched_fields: list[str] = []
    for field_name, matched in matched_by_field:
        new_tokens = matched - covered
        if new_tokens:
            matched_fields.append(field_name)
            covered.update(new_tokens)

    if not covered:
        return 0.0, ()

    matched_weight = 0.0
    for token in query_tokens:
        weights = [
            weight
            for field_name, weight in _FIELD_WEIGHTS
            if token in field_tokens[field_name]
        ]
        matched_weight += max(weights, default=0.0)

    score = matched_weight / len(query_tokens)
    return score, tuple(matched_fields)


class CatalogTextRetrievalEngine:
    """Rank active catalog rows by deterministic lexical metadata overlap."""

    def search(
        self,
        query: str,
        rows: list[TrackRow],
        *,
        limit: int = 10,
        expand: bool = False,
    ) -> list[TextSearchResult]:
        if query is None or not query.strip():
            raise ValueError("query must be non-empty")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        queries = expand_query(query) if expand else (query,)
        query_tokens = [_tokens(value) for value in queries]
        if not any(query_tokens):
            raise ValueError("query must contain searchable text")

        results: list[TextSearchResult] = []
        for row in rows:
            if row.status != "active":
                continue

            best_score = 0.0
            best_fields: tuple[str, ...] = ()
            for tokens in query_tokens:
                score, matched_fields = _field_score(tokens, row)
                if score > best_score or (
                    score == best_score and matched_fields < best_fields
                ):
                    best_score = score
                    best_fields = matched_fields

            if best_score <= 0:
                continue
            results.append(
                TextSearchResult(
                    track_id=row.track_id,
                    score=best_score,
                    matched_fields=best_fields,
                    title=row.title,
                    artist=row.artist,
                    album=row.album,
                )
            )

        results.sort(key=lambda item: (-item.score, item.track_id))
        return results[:limit]
