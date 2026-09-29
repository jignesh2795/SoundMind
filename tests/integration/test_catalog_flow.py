from datetime import UTC, datetime

from soundmind.catalog import CatalogCandidateRepository
from soundmind.flow import EndToEndMusicFlow, EndToEndRequest
from soundmind.sequence import SequenceMode
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


def track(\n    track_id: str,\n    *,\n    genre: str,\n    energy: float,\n    tempo: float,\n    sample_rate: int | None = None,\n    spectral_centroid: float | None = None,\n    mfcc_json: str | None = None,\n    chroma_json: str | None = None,\n) -> TrackRow:
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
        genre=genre,
        rms_energy=energy,
        tempo_bpm=tempo,
    )


def test_sqlite_catalog_feeds_m5_end_to_end_flow(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        session.add_all(
            [
                track("a", genre="cinematic", energy=0.35, tempo=90.0),
                track("b", genre="cinematic", energy=0.65, tempo=110.0),
                track("c", genre="folk", energy=0.85, tempo=130.0),
                track("missing", genre="cinematic", energy=0.9, tempo=140.0),
            ]
        )
        session.commit()
        session.get(TrackRow, "missing").status = "missing"
        session.commit()

        catalog = CatalogCandidateRepository(session)
        catalog_rows = catalog.candidates()

        result = EndToEndMusicFlow().run(
            EndToEndRequest(
                text="cinematic BGM",
                candidates=tuple(item.candidate for item in catalog_rows),
                mode=SequenceMode.SMOOTH,
                limit=2,
            )
        )

    assert [item.candidate.intent_candidate.track_id for item in catalog_rows] == ["a", "b", "c"]
    assert [item.track_id for item in result.ranked] == ["a", "b"]
    assert [item.track_id for item in result.playlist] == ["a", "b"]


def test_catalog_adapter_preserves_missing_intent_evidence_as_unknown(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        row = track("a", genre="cinematic", energy=0.5, tempo=100.0)
        session.add(row)
        session.commit()

        candidate = CatalogCandidateRepository(session).candidates()[0].candidate.intent_candidate

    assert candidate.genres == ("cinematic",)
    assert candidate.languages == ()
    assert candidate.regions == ()
    assert candidate.moods == ()
    assert candidate.music_types == ()
    assert candidate.scenes == ()
    assert candidate.vocal_preference == "any"
    assert candidate.novelty_score == 0.0
    assert candidate.energy == 0.5


def test_catalog_maps_stored_audio_evidence_to_music_dna(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        session.add(
            track(
                "a",
                genre="cinematic",
                energy=0.5,
                tempo=100.0,
                sample_rate=16000,
                spectral_centroid=4000.0,
                mfcc_json="[1.0, 2.0]",
                chroma_json="[0.1, 0.2]",
            )
        )
        session.commit()

        item = CatalogCandidateRepository(session).candidates()[0]

    assert item.music_dna.tempo_bpm == 100.0
    assert item.music_dna.energy == 0.5
    assert item.music_dna.brightness == 0.5
    assert item.music_dna.mfcc == (1.0, 2.0)
    assert item.music_dna.chroma == (0.1, 0.2)
    assert item.candidate.brightness == 0.5
