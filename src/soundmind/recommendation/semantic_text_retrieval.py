"""Semantic text retrieval over catalog metadata using local embeddings."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from soundmind.storage.models import TrackRow

DEFAULT_TEXT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_TEXT_QUERY_PREFIX = "query: "
DEFAULT_TEXT_DOCUMENT_PREFIX = "passage: "

_TEXT_FIELDS = (
    ("title", "title"),
    ("artist", "artist"),
    ("album", "album"),
    ("album_artist", "album artist"),
    ("composer", "composer"),
    ("genre", "genre"),
    ("file_name", "file name"),
)


@dataclass(frozen=True)
class TextEmbeddingProfile:
    """Describe a text embedding model and its query/document prefixes."""

    model_name: str
    query_prefix: str = DEFAULT_TEXT_QUERY_PREFIX
    document_prefix: str = DEFAULT_TEXT_DOCUMENT_PREFIX

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name must be non-empty")


@dataclass(frozen=True)
class SemanticTextSearchResult:
    """A semantic catalog-search result."""

    track_id: str
    score: float
    title: str | None = None
    artist: str | None = None
    album: str | None = None


class TextEmbeddingProvider(Protocol):
    """Provide query and document text embeddings."""

    def embed_query(self, text: str) -> Sequence[float]:
        """Embed one search query."""

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Embed catalog metadata documents in input order."""


def catalog_text(row: TrackRow) -> str:
    """Build a stable labeled text representation from catalog metadata."""
    parts = [
        f"{label}: {value}"
        for field_name, label in _TEXT_FIELDS
        if (value := getattr(row, field_name))
    ]
    return " | ".join(parts)


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    if not left:
        raise ValueError("embeddings must be non-empty")

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right, strict=True):
        if not math.isfinite(left_value) or not math.isfinite(right_value):
            raise ValueError("embeddings must contain finite values")
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value

    denominator = math.sqrt(left_norm * right_norm)
    if denominator == 0.0:
        return 0.0
    return dot / denominator


class SemanticTextRetrievalEngine:
    """Rank active catalog rows by local semantic text similarity."""

    def __init__(self, provider: TextEmbeddingProvider) -> None:
        self._provider = provider

    def search(
        self,
        query: str,
        rows: list[TrackRow],
        *,
        limit: int = 10,
    ) -> list[SemanticTextSearchResult]:
        if query is None or not query.strip():
            raise ValueError("query must be non-empty")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        active_rows = [row for row in rows if row.status == "active"]
        if not active_rows:
            return []

        seen: set[str] = set()
        for row in active_rows:
            if row.track_id in seen:
                raise ValueError(f"duplicate track_id: {row.track_id!r}")
            seen.add(row.track_id)

        query_vector = self._provider.embed_query(query.strip())
        documents = [catalog_text(row) for row in active_rows]
        document_vectors = self._provider.embed_documents(documents)

        if len(document_vectors) != len(active_rows):
            raise ValueError("embedding provider returned the wrong document count")

        results = [
            SemanticTextSearchResult(
                track_id=row.track_id,
                score=_cosine_similarity(query_vector, vector),
                title=row.title,
                artist=row.artist,
                album=row.album,
            )
            for row, vector in zip(active_rows, document_vectors, strict=True)
        ]
        results.sort(key=lambda item: (-item.score, item.track_id))
        return results[:limit]


class FastEmbedTextProvider:
    """Optional FastEmbed adapter for CPU-oriented local text embeddings."""

    def __init__(
        self,
        model_name: str = DEFAULT_TEXT_MODEL,
        *,
        query_prefix: str = DEFAULT_TEXT_QUERY_PREFIX,
        document_prefix: str = DEFAULT_TEXT_DOCUMENT_PREFIX,
    ) -> None:
        self.profile = TextEmbeddingProfile(
            model_name=model_name,
            query_prefix=query_prefix,
            document_prefix=document_prefix,
        )
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "semantic search requires optional dependency 'fastembed'; "
                "install it with: uv pip install fastembed"
            ) from exc

        self._model = TextEmbedding(model_name=self.profile.model_name)

    def embed_query(self, text: str) -> Sequence[float]:
        """Embed a query with the configured query prefix."""
        return next(iter(self._model.embed([f"{self.profile.query_prefix}{text}"])))

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Embed catalog metadata with the configured document prefix."""
        return tuple(
            self._model.embed(
                [f"{self.profile.document_prefix}{text}" for text in texts]
            )
        )
