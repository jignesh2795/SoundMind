"""SQLite-backed application boundary for deterministic catalog text search."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from soundmind.recommendation.text_retrieval import CatalogTextRetrievalEngine, TextSearchResult
from soundmind.storage.models import TrackRow


class CatalogTextSearchService:
    """Search active SQLite catalog metadata using deterministic lexical retrieval."""

    def __init__(
        self,
        session: Session,
        *,
        engine: CatalogTextRetrievalEngine | None = None,
    ) -> None:
        self._session = session
        self._engine = engine or CatalogTextRetrievalEngine()

    def search(self, query: str, *, limit: int = 10) -> list[TextSearchResult]:
        rows = list(
            self._session.scalars(
                select(TrackRow)
                .where(TrackRow.status == "active")
                .order_by(TrackRow.track_id)
            )
        )
        return self._engine.search(query, rows, limit=limit)
