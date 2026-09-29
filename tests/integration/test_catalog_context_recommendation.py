from datetime import UTC, datetime

import pytest

from soundmind.catalog_recommendation import CatalogContextRecommendationService
from soundmind.flow import EndToEndRequest
from soundmind.preferences.models import ListeningEvent, ListeningEventType
from soundmind.preferences.repository import ListeningEventRepository
from soundmind.recommendation.fusion import FusionWeights
from soundmind.sequence import SequenceMode
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def track(track_id: str, *, genre: str = "cinematic", status: str = "active") -> TrackRow:
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
        title=f"Track {track_id}",
        genre=genre,
        rms_energy=0.5,
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
    assert [item.track_id for item in result.playlist] == [item.track_id for item in result.ranked]


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
