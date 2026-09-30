"""SQLite-backed application boundary for context-aware recommendations."""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from soundmind.catalog import CatalogCandidate, CatalogCandidateRepository
from soundmind.catalog_search import CatalogTextSearchService
from soundmind.context_aware_flow import ContextAwareMusicFlow
from soundmind.flow import EndToEndRequest, EndToEndResult
from soundmind.preferences.repository import ListeningEventRepository
from soundmind.recommendation.semantic_text_retrieval import TextEmbeddingProvider

DEFAULT_RETRIEVAL_LIMIT = 50
RETRIEVAL_MODES = (
    "catalog",
    "lexical",
    "semantic",
    "semantic-indexed",
    "hybrid",
    "hybrid-indexed",
)


class CatalogContextRecommendationService:
    """Build a context-aware recommendation from persisted catalog and history."""

    def __init__(
        self,
        session: Session,
        *,
        flow: ContextAwareMusicFlow | None = None,
    ) -> None:
        self._session = session
        self._catalog = CatalogCandidateRepository(session)
        self._events = ListeningEventRepository(session)
        self._flow = flow or ContextAwareMusicFlow()

    def _retrieved_candidates(
        self,
        query: str,
        *,
        mode: str,
        limit: int,
        provider: TextEmbeddingProvider | None,
        model_name: str | None,
        index_path: Path | None,
    ) -> list[CatalogCandidate]:
        search = CatalogTextSearchService(self._session)

        if mode == "lexical":
            results = search.search(query, limit=limit)
        elif mode == "semantic":
            if provider is None:
                raise ValueError("text embedding provider is required for semantic retrieval")
            results = search.semantic_search(query, provider=provider, limit=limit)
        elif mode == "semantic-indexed":
            if provider is None:
                raise ValueError(
                    "text embedding provider is required for persisted semantic retrieval"
                )
            if not model_name:
                raise ValueError("text model name is required for persisted semantic retrieval")
            if index_path is None:
                raise ValueError("text index path is required for persisted semantic retrieval")
            results = search.semantic_search_indexed(
                query,
                provider=provider,
                model_name=model_name,
                index_path=index_path,
                limit=limit,
            )
        elif mode == "hybrid":
            if provider is None:
                raise ValueError("text embedding provider is required for hybrid retrieval")
            results = search.hybrid_search(query, provider=provider, limit=limit)
        elif mode == "hybrid-indexed":
            if provider is None:
                raise ValueError(
                    "text embedding provider is required for persisted hybrid retrieval"
                )
            if not model_name:
                raise ValueError("text model name is required for persisted hybrid retrieval")
            if index_path is None:
                raise ValueError("text index path is required for persisted hybrid retrieval")
            results = search.hybrid_search_indexed(
                query,
                provider=provider,
                model_name=model_name,
                index_path=index_path,
                limit=limit,
            )
        else:
            raise ValueError(f"unsupported retrieval mode: {mode!r}")

        return self._catalog.candidates_by_ids(
            result.track_id for result in results
        )

    @staticmethod
    def _validate_retrieval_mode(mode: str) -> None:
        if mode not in RETRIEVAL_MODES:
            choices = ", ".join(RETRIEVAL_MODES)
            raise ValueError(f"unsupported retrieval mode: {mode!r}; choose from {choices}")

    @staticmethod
    def _retrieval_limit(
        request: EndToEndRequest,
        retrieval_limit: int | None,
    ) -> int:
        effective = retrieval_limit if retrieval_limit is not None else max(
            DEFAULT_RETRIEVAL_LIMIT,
            request.limit,
        )
        if isinstance(effective, bool) or not isinstance(effective, int) or effective <= 0:
            raise ValueError("retrieval_limit must be a positive integer")
        return effective

    def recommend(
        self,
        request: EndToEndRequest,
        *,
        context: str,
        now: datetime,
        event_limit: int = 1000,
        catalog_limit: int | None = None,
        seed_track_id: str | None = None,
        retrieval_mode: str = "catalog",
        retrieval_limit: int | None = None,
        text_provider: TextEmbeddingProvider | None = None,
        text_model: str | None = None,
        text_index_path: Path | None = None,
    ) -> EndToEndResult:
        self._validate_retrieval_mode(retrieval_mode)

        if retrieval_mode == "catalog":
            catalog_rows = self._catalog.candidates(limit=catalog_limit)
        else:
            if catalog_limit is not None:
                raise ValueError(
                    "catalog_limit cannot be combined with a non-catalog retrieval mode"
                )
            catalog_rows = self._retrieved_candidates(
                request.text,
                mode=retrieval_mode,
                limit=self._retrieval_limit(request, retrieval_limit),
                provider=text_provider,
                model_name=text_model,
                index_path=text_index_path,
            )

        events = self._events.list_recent(limit=event_limit)
        persisted_request = EndToEndRequest(
            text=request.text,
            candidates=tuple(item.candidate for item in catalog_rows),
            mode=request.mode,
            seed_track_id=request.seed_track_id,
            limit=request.limit,
            weights=request.weights,
        )
        effective_seed = (
            seed_track_id
            if seed_track_id is not None
            else request.seed_track_id
        )
        return self._flow.run(
            persisted_request,
            events=events,
            context=context,
            now=now,
            seed_track_id=effective_seed,
        )
