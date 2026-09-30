from datetime import UTC, datetime

import pytest

from soundmind.catalog_recommendation import CatalogContextRecommendationService
from soundmind.catalog_search import CatalogTextSearchService
from soundmind.flow import EndToEndRequest
from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.preferences.repository import ListeningEventRepository
from soundmind.recommendation.fusion import FusionWeights
from soundmind.sequence import SequenceMode
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def track(
    track_id: str,
    *,
    genre: str = "cinematic",
    status: str = "active",
    title: str | None = None,
    energy: float = 0.5,
) -> TrackRow:
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1000,
        modified_at_ns=1,
        status=status,
        created_at=NOW,
        updated_at=NOW,
        title=title or f"Track {track_id}",
        genre=genre,
        rms_energy=energy,
        tempo_bpm=100.0,
    )


def test_sqlite_catalog_and_events_feed_context_aware_flow(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all([track("seen"), track("new")])
        session.commit()

        ListeningEventRepository(session).add(
            ListeningEvent("seen", ListeningEventType.LIKE, NOW, context="coding")
        )

        request = EndToEndRequest(
            text="cinematic BGM",
            candidates=[],
            mode=SequenceMode.SMOOTH,
            limit=2,
            weights=FusionWeights(
                metadata=0.0,
                dsp=0.0,
                learned=0.0,
                preference=0.5,
                novelty=0.5,
                diversity=0.0,
            ),
        )
        result = CatalogContextRecommendationService(session).recommend(
            request,
            context="coding",
            now=NOW,
        )

    by_id = {item.track_id: item for item in result.ranked}
    assert by_id["seen"].signals.preference_score == pytest.approx(
        0.46211715726000974
    )
    assert by_id["seen"].signals.novelty_score == pytest.approx(0.5)
    assert by_id["new"].signals.preference_score == pytest.approx(0.0)
    assert by_id["new"].signals.novelty_score == pytest.approx(1.0)
    assert [item.track_id for item in result.playlist] == [
        item.track_id for item in result.ranked
    ]


def test_inactive_catalog_tracks_are_excluded(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all([track("active"), track("inactive", status="missing")])
        session.commit()

        request = EndToEndRequest(
            text="cinematic BGM",
            candidates=[],
            limit=10,
        )
        result = CatalogContextRecommendationService(session).recommend(
            request,
            context="coding",
            now=NOW,
        )

    assert [item.track_id for item in result.ranked] == ["active"]


def test_catalog_context_service_is_deterministic(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all([track("a"), track("b")])
        session.commit()

        request = EndToEndRequest(
            text="cinematic BGM",
            candidates=[],
            limit=2,
        )
        service = CatalogContextRecommendationService(session)

        first = service.recommend(request, context="coding", now=NOW)
        second = service.recommend(request, context="coding", now=NOW)

    assert first == second


class StaticTextProvider:
    def embed_query(self, text: str):
        return (1.0, 0.0)

    def embed_documents(self, texts):
        return tuple(
            (1.0, 0.0) if "semantic" in text.casefold() else (0.0, 1.0)
            for text in texts
        )


def test_hybrid_retrieval_feeds_existing_ranking_and_sequence(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all(
            [
                track(
                    "lexical",
                    title="High Energy Entry",
                    energy=0.8,
                ),
                track(
                    "semantic",
                    title="Semantic Track",
                    genre="ambient",
                    energy=0.3,
                ),
                track(
                    "excluded",
                    title="Other Track",
                    genre="ambient",
                    energy=0.3,
                ),
            ]
        )
        session.commit()

        request = EndToEndRequest(
            text="high energy",
            candidates=[],
            mode=SequenceMode.SMOOTH,
            limit=2,
        )
        result = CatalogContextRecommendationService(session).recommend(
            request,
            context="coding",
            now=NOW,
            retrieval_mode="hybrid",
            retrieval_limit=1,
            text_provider=StaticTextProvider(),
        )

    assert [item.track_id for item in result.ranked] == ["lexical", "semantic"]
    assert [item.track_id for item in result.playlist] == ["lexical", "semantic"]


def test_hybrid_indexed_retrieval_feeds_recommendation(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    index_path = tmp_path / "semantic_vectors"

    with session_factory() as session:
        session.add_all(
            [
                track("lexical", title="High Energy Entry", energy=0.8),
                track(
                    "semantic",
                    title="Semantic Track",
                    genre="ambient",
                    energy=0.3,
                ),
            ]
        )
        session.commit()

        provider = StaticTextProvider()
        CatalogTextSearchService(session).rebuild_semantic_index(
            provider=provider,
            model_name="model-v1",
            index_path=index_path,
        )

        request = EndToEndRequest(
            text="high energy",
            candidates=[],
            mode=SequenceMode.SMOOTH,
            limit=2,
        )
        result = CatalogContextRecommendationService(session).recommend(
            request,
            context="coding",
            now=NOW,
            retrieval_mode="hybrid-indexed",
            retrieval_limit=1,
            text_provider=provider,
            text_model="model-v1",
            text_index_path=index_path,
        )

    assert [item.track_id for item in result.ranked] == ["lexical", "semantic"]


def test_non_catalog_retrieval_rejects_catalog_limit(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        request = EndToEndRequest(text="high energy", candidates=[], limit=1)

        with pytest.raises(ValueError, match="catalog_limit"):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                catalog_limit=10,
                retrieval_mode="lexical",
            )


def test_hybrid_retrieval_requires_text_provider(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        request = EndToEndRequest(text="high energy", candidates=[], limit=1)

        with pytest.raises(ValueError, match="text embedding provider"):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                retrieval_mode="hybrid",
                retrieval_limit=1,
            )
