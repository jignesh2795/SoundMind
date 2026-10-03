import copy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from soundmind.catalog_recommendation import CatalogContextRecommendationService
from soundmind.catalog_search import CatalogTextSearchService
from soundmind.flow import EndToEndRequest, EndToEndResult
from soundmind.intent import parse_intent
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
            retrieval_limit=2,
            text_provider=StaticTextProvider(),
        )

    assert [item.track_id for item in result.ranked] == ["lexical", "semantic"]
    assert [item.track_id for item in result.playlist] == ["lexical", "semantic"]


def test_hybrid_recommendation_weights_control_candidate_pool(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all(
            [
                track("lexical", title="Hero Entry", genre="cinematic"),
                track("mixed", title="Hero", genre="semantic"),
                track("semantic", title="Unrelated Track", genre="semantic"),
            ]
        )
        session.commit()

        request = EndToEndRequest(
            text="hero entry",
            candidates=[],
            mode=SequenceMode.SMOOTH,
            limit=2,
        )
        provider = StaticTextProvider()
        service = CatalogContextRecommendationService(session)

        lexical_first = service.recommend(
            request,
            context="coding",
            now=NOW,
            retrieval_mode="hybrid",
            retrieval_limit=2,
            text_provider=provider,
            lexical_weight=1.0,
            semantic_weight=0.0,
        )
        semantic_first = service.recommend(
            request,
            context="coding",
            now=NOW,
            retrieval_mode="hybrid",
            retrieval_limit=2,
            text_provider=provider,
            lexical_weight=0.0,
            semantic_weight=1.0,
        )

    assert {item.track_id for item in lexical_first.ranked} == {"lexical", "mixed"}
    assert {item.track_id for item in semantic_first.ranked} == {"mixed", "semantic"}


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
            retrieval_limit=2,
            text_provider=provider,
            text_model="model-v1",
            text_index_path=index_path,
        )

    assert [item.track_id for item in result.ranked] == ["lexical", "semantic"]


def test_hybrid_recommendation_rejects_invalid_weights(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(track("hero", title="Hero Entry"))
        session.commit()

        request = EndToEndRequest(text="hero", candidates=[], limit=1)

        with pytest.raises(ValueError, match="weight"):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                retrieval_mode="hybrid",
                retrieval_limit=1,
                text_provider=StaticTextProvider(),
                lexical_weight=-0.1,
                semantic_weight=0.5,
            )


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


def test_recommend_rejects_invalid_retrieval_mode(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        request = EndToEndRequest(text="cinematic BGM", candidates=[], limit=2)

        with pytest.raises(ValueError, match="choose from"):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                retrieval_mode="bogus",
            )


@pytest.mark.parametrize("limit", [0, -1, True, False, "25", 2.5])
def test_recommend_rejects_invalid_retrieval_limit(tmp_path, limit) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(track("a"))
        session.commit()
        request = EndToEndRequest(text="cinematic", candidates=[], limit=2)

        with pytest.raises(ValueError, match="retrieval_limit must be a positive integer"):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                retrieval_mode="lexical",
                retrieval_limit=limit,
            )


def test_retrieval_limit_defaults_to_fifty_or_request_limit() -> None:
    service = CatalogContextRecommendationService.__new__(CatalogContextRecommendationService)

    small = EndToEndRequest(text="cinematic", candidates=[], limit=3)
    large = EndToEndRequest(text="cinematic", candidates=[], limit=100)

    assert service._retrieval_limit(small, None) == 50
    assert service._retrieval_limit(large, None) == 100
    assert service._retrieval_limit(small, 7) == 7


def test_semantic_retrieval_requires_provider(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(track("a"))
        session.commit()
        request = EndToEndRequest(text="cinematic", candidates=[], limit=1)

        with pytest.raises(ValueError, match="text embedding provider"):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                retrieval_mode="semantic",
                retrieval_limit=1,
            )


@pytest.mark.parametrize(
    ("mode", "kwargs", "message"),
    [
        ("semantic-indexed", {"text_model": ""}, "text model name is required"),
        ("semantic-indexed", {"text_index_path": None}, "text index path is required"),
        ("hybrid-indexed", {"text_model": ""}, "text model name is required"),
        ("hybrid-indexed", {"text_index_path": None}, "text index path is required"),
    ],
)
def test_indexed_retrieval_requires_model_and_index(tmp_path, mode, kwargs, message) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(track("a"))
        session.commit()
        request = EndToEndRequest(text="cinematic", candidates=[], limit=1)
        options = {
            "text_provider": object(),
            "text_model": "model-v1",
            "text_index_path": Path("index"),
        }
        options.update(kwargs)

        with pytest.raises(ValueError, match=message):
            CatalogContextRecommendationService(session).recommend(
                request,
                context="coding",
                now=NOW,
                retrieval_mode=mode,
                retrieval_limit=1,
                **options,
            )


def test_event_limit_is_forwarded_to_repository(monkeypatch, tmp_path) -> None:
    captured = []

    class FakeEvents:
        def __init__(self, session) -> None:
            pass

        def list_recent(self, limit=1000):
            captured.append(limit)
            return []

    monkeypatch.setattr("soundmind.catalog_recommendation.ListeningEventRepository", FakeEvents)
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(track("a"))
        session.commit()
        request = EndToEndRequest(text="cinematic", candidates=[], limit=1)
        service = CatalogContextRecommendationService(session)
        service.recommend(request, context="coding", now=NOW, event_limit=5)
        service.recommend(request, context="coding", now=NOW)

    assert captured == [5, 1000]


def test_explicit_seed_overrides_request_seed(tmp_path) -> None:
    captured = []

    class FakeFlow:
        def run(self, request, *, events, context, now, seed_track_id):
            captured.append(seed_track_id)
            return EndToEndResult(intent=parse_intent("dark BGM"), ranked=(), playlist=())

    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add_all([track("a"), track("b")])
        session.commit()
        service = CatalogContextRecommendationService(session, flow=FakeFlow())

        explicit = EndToEndRequest(text="dark BGM", candidates=[], limit=2, seed_track_id="a")
        service.recommend(explicit, context="coding", now=NOW, seed_track_id="b")
        fallback = EndToEndRequest(text="dark BGM", candidates=[], limit=2, seed_track_id="a")
        service.recommend(fallback, context="coding", now=NOW)

    assert captured == ["b", "a"]


def test_recommend_does_not_mutate_request_or_catalog(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    def snapshot(session):
        return [
            (row.track_id, row.status, row.title, row.genre)
            for row in session.scalars(select(TrackRow)).all()
        ]

    with session_factory() as session:
        session.add_all([track("a"), track("b")])
        session.commit()
        ListeningEventRepository(session).add(
            ListeningEvent("a", ListeningEventType.LIKE, NOW, context="coding")
        )

        request = EndToEndRequest(text="cinematic BGM", candidates=[], limit=2)
        before_request = copy.deepcopy(request)
        before_rows = snapshot(session)
        before_events = [
            (event.track_id, event.event_type, event.context)
            for event in ListeningEventRepository(session).list_recent()
        ]

        CatalogContextRecommendationService(session).recommend(request, context="coding", now=NOW)
        session.expire_all()

        assert request == before_request
        assert snapshot(session) == before_rows
        assert [
            (event.track_id, event.event_type, event.context)
            for event in ListeningEventRepository(session).list_recent()
        ] == before_events


def test_lexical_retrieval_needs_no_provider(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    with session_factory() as session:
        session.add(track("hero", title="Hero Entry"))
        session.commit()
        request = EndToEndRequest(text="hero entry", candidates=[], limit=2)

        result = CatalogContextRecommendationService(session).recommend(
            request,
            context="coding",
            now=NOW,
            retrieval_mode="lexical",
        )

    assert [item.track_id for item in result.ranked] == ["hero"]
