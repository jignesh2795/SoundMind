"""SQLite-backed application boundary for context-aware recommendations."""

from datetime import datetime

from sqlalchemy.orm import Session

from soundmind.catalog import CatalogCandidateRepository
from soundmind.context_aware_flow import ContextAwareMusicFlow
from soundmind.flow import EndToEndRequest, EndToEndResult
from soundmind.preferences.repository import ListeningEventRepository


class CatalogContextRecommendationService:
    """Build a context-aware recommendation from persisted catalog and history."""

    def __init__(
        self,
        session: Session,
        *,
        flow: ContextAwareMusicFlow | None = None,
    ) -> None:
        self._catalog = CatalogCandidateRepository(session)
        self._events = ListeningEventRepository(session)
        self._flow = flow or ContextAwareMusicFlow()

    def recommend(
        self,
        request: EndToEndRequest,
        *,
        context: str,
        now: datetime,
        event_limit: int = 1000,
        catalog_limit: int | None = None,
        seed_track_id: str | None = None,
    ) -> EndToEndResult:
        catalog_rows = self._catalog.candidates(limit=catalog_limit)
        events = self._events.list_recent(limit=event_limit)
        persisted_request = EndToEndRequest(
            text=request.text,
            candidates=tuple(item.candidate for item in catalog_rows),
            mode=request.mode,
            seed_track_id=request.seed_track_id,
            limit=request.limit,
            weights=request.weights,
        )
        effective_seed = seed_track_id if seed_track_id is not None else request.seed_track_id
        return self._flow.run(
            persisted_request,
            events=events,
            context=context,
            now=now,
            seed_track_id=effective_seed,
        )
