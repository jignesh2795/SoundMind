"""SQLite-backed application boundary for catalog text search."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from soundmind.recommendation.semantic_text_index import PersistentSemanticTextIndex
from soundmind.recommendation.semantic_text_retrieval import (
    SemanticTextRetrievalEngine,
    SemanticTextSearchResult,
    TextEmbeddingProvider,
)
from soundmind.recommendation.text_retrieval import CatalogTextRetrievalEngine, TextSearchResult
from soundmind.storage.models import TrackRow


class CatalogTextSearchService:
    """Search active SQLite catalog metadata with lexical or semantic retrieval."""

    def __init__(
        self,
        session: Session,
        *,
        engine: CatalogTextRetrievalEngine | None = None,
        semantic_engine: SemanticTextRetrievalEngine | None = None,
    ) -> None:
        self._session = session
        self._engine = engine or CatalogTextRetrievalEngine()
        self._semantic_engine = semantic_engine

    def _active_rows(self) -> list[TrackRow]:
        return list(
            self._session.scalars(
                select(TrackRow)
                .where(TrackRow.status == "active")
                .order_by(TrackRow.track_id)
            )
        )

    def search(self, query: str, *, limit: int = 10) -> list[TextSearchResult]:
        return self._engine.search(query, self._active_rows(), limit=limit)

    def semantic_search(
        self,
        query: str,
        *,
        provider: TextEmbeddingProvider,
        limit: int = 10,
    ) -> list[SemanticTextSearchResult]:
        engine = self._semantic_engine or SemanticTextRetrievalEngine(provider)
        return engine.search(query, self._active_rows(), limit=limit)

    def rebuild_semantic_index(
        self,
        *,
        provider: TextEmbeddingProvider,
        model_name: str,
        index_path,
    ) -> int:
        index = PersistentSemanticTextIndex(index_path)
        return index.rebuild(
            self._active_rows(),
            provider=provider,
            model_name=model_name,
        )

    def semantic_search_indexed(
        self,
        query: str,
        *,
        provider: TextEmbeddingProvider,
        model_name: str,
        index_path,
        limit: int = 10,
    ) -> list[SemanticTextSearchResult]:
        index = PersistentSemanticTextIndex(index_path)
        scores = index.search(
            query,
            self._active_rows(),
            provider=provider,
            model_name=model_name,
            limit=limit,
        )
        rows_by_id = {row.track_id: row for row in self._active_rows()}
        return [
            SemanticTextSearchResult(
                track_id=track_id,
                score=score,
                title=rows_by_id[track_id].title,
                artist=rows_by_id[track_id].artist,
                album=rows_by_id[track_id].album,
            )
            for track_id, score in scores
            if track_id in rows_by_id
        ]
