from datetime import UTC, datetime

import pytest

from soundmind.catalog import CatalogCandidateRepository
from soundmind.flow import EndToEndRequest
from soundmind.learned_flow import LearnedEndToEndMusicFlow
from soundmind.recommendation.learned_retrieval import LearnedRetrievalEngine
from soundmind.sequence import SequenceMode
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow
from soundmind.vector.index import SimilarityResult


class FakeSimilarityProvider:
    def similar(self, track_id: str, *, limit: int = 10):
        assert track_id == "seed"
        return [
            SimilarityResult("b", 0.9),
            SimilarityResult("a", 0.1),
        ][:limit]


def track(track_id: str, energy: float) -> TrackRow:
    now = datetime.now(UTC)
    return TrackRow(
        track_id=track_id,
        content_hash=track_id * 64,
        source_type="file",
        source_uri=f"file:///music/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1000,
        modified_at_ns=1,
        status="active",
        created_at=now,
        updated_at=now,
        title=f"Track {track_id}",
        genre="cinematic",
        rms_energy=energy,
        tempo_bpm=100.0,
    )


def test_sqlite_catalog_feeds_learned_similarity_into_m1(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        session.add_all(
            [
                track("seed", 0.5),
                track("a", 0.5),
                track("b", 0.5),
            ]
        )
        session.commit()

        catalog = CatalogCandidateRepository(session)
        catalog_rows = catalog.candidates()
        request = EndToEndRequest(
            text="cinematic BGM",
            candidates=tuple(item.candidate for item in catalog_rows),
            mode=SequenceMode.SMOOTH,
            limit=2,
        )
        flow = LearnedEndToEndMusicFlow(
            LearnedRetrievalEngine(FakeSimilarityProvider())
        )
        result = flow.run(request, seed_track_id="seed")

    assert [item.track_id for item in result.ranked] == ["b", "a"]
    assert result.ranked[0].signals.learned_score == pytest.approx(0.95)
    assert result.ranked[1].signals.learned_score == pytest.approx(0.55)
    assert [item.track_id for item in result.playlist] == ["b", "a"]
