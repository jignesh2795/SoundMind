from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from soundmind.catalog import (
    CatalogCandidateRepository,
    candidate_from_row,
    end_to_end_candidates,
    music_dna_from_row,
)
from soundmind.flow import EndToEndMusicFlow, EndToEndRequest
from soundmind.sequence import SequenceMode
from soundmind.storage.database import create_session_factory
from soundmind.storage.models import TrackRow


def track(
    track_id: str,
    *,
    genre: str,
    energy: float,
    tempo: float,
    sample_rate: int | None = None,
    spectral_centroid: float | None = None,
    mfcc_json: str | None = None,
    chroma_json: str | None = None,
) -> TrackRow:
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
        sample_rate=sample_rate,
        spectral_centroid=spectral_centroid,
        mfcc_json=mfcc_json,
        chroma_json=chroma_json,
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


def test_candidates_limit_truncates_in_track_id_order(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        session.add_all(
            [
                track("a", genre="cinematic", energy=0.35, tempo=90.0),
                track("b", genre="cinematic", energy=0.65, tempo=110.0),
                track("c", genre="folk", energy=0.85, tempo=130.0),
            ]
        )
        session.commit()

        rows = CatalogCandidateRepository(session).candidates(limit=2)

    assert [item.candidate.intent_candidate.track_id for item in rows] == ["a", "b"]


@pytest.mark.parametrize("limit", [0, -1, True, False, "2", 2.5])
def test_candidates_rejects_invalid_limits(tmp_path, limit) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with (
        session_factory() as session,
        pytest.raises(ValueError, match="limit must be a positive integer"),
    ):
        CatalogCandidateRepository(session).candidates(limit=limit)


def test_candidates_by_ids_empty_returns_empty(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        assert CatalogCandidateRepository(session).candidates_by_ids([]) == []


@pytest.mark.parametrize("track_ids", [["a", "a"], ["a", ""]])
def test_candidates_by_ids_rejects_duplicate_and_blank(tmp_path, track_ids) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        session.add(track("a", genre="cinematic", energy=0.5, tempo=100.0))
        session.commit()

        with pytest.raises(ValueError):
            CatalogCandidateRepository(session).candidates_by_ids(track_ids)


def test_candidates_by_ids_active_only_and_ordered(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")
    with session_factory() as session:
        stale = track("c", genre="cinematic", energy=0.9, tempo=140.0)
        stale.status = "inactive"
        session.add_all(
            [
                track("a", genre="cinematic", energy=0.35, tempo=90.0),
                track("b", genre="cinematic", energy=0.65, tempo=110.0),
                stale,
            ]
        )
        session.commit()

        rows = CatalogCandidateRepository(session).candidates_by_ids(["c", "b", "a"])

    assert [item.candidate.intent_candidate.track_id for item in rows] == ["b", "a"]


@pytest.mark.parametrize("vectors", [None, "", "not-json", '{"a": 1.0}', "[1.0, 'x']"])
def test_malformed_vectors_are_unknown(vectors) -> None:
    row = TrackRow(track_id="x", mfcc_json=vectors, chroma_json=vectors)

    assert music_dna_from_row(row).mfcc == ()
    assert music_dna_from_row(row).chroma == ()


@pytest.mark.parametrize(
    ("stored", "expected"),
    [(-0.5, 0.0), (1.5, 1.0), (None, None), (0.5, 0.5)],
)
def test_bounded_energy_clamps(stored, expected) -> None:
    row = TrackRow(track_id="x", rms_energy=stored)

    assert music_dna_from_row(row).energy == expected


def test_neutral_unknown_evidence() -> None:
    row = TrackRow(track_id="x")

    candidate = candidate_from_row(row).candidate.intent_candidate
    dna = candidate_from_row(row).music_dna

    assert candidate.genres == ()
    assert candidate.energy is None
    assert candidate.vocal_preference == "any"
    assert candidate.novelty_score == 0.0
    assert candidate.base_signals.learned_score == 0.0
    assert candidate.base_signals.preference_score == 0.0
    assert candidate.base_signals.diversity_score == 0.0
    assert dna.brightness is None
    assert dna.mfcc == ()
    assert dna.chroma == ()


def test_adapter_does_not_mutate_catalog(tmp_path) -> None:
    session_factory = create_session_factory(tmp_path / "soundmind.db")

    def snapshot(session):
        return [
            (row.track_id, row.status, row.title, row.genre, row.rms_energy)
            for row in session.scalars(select(TrackRow)).all()
        ]

    with session_factory() as session:
        session.add_all(
            [
                track("a", genre="cinematic", energy=0.35, tempo=90.0),
                track("b", genre="cinematic", energy=0.65, tempo=110.0),
            ]
        )
        session.commit()

        repository = CatalogCandidateRepository(session)
        before = snapshot(session)
        repository.candidates()
        repository.candidates(limit=1)
        rows = session.scalars(select(TrackRow)).all()
        repository.candidates_by_ids(["b", "a"])
        end_to_end_candidates(rows)
        session.expire_all()

        assert snapshot(session) == before


def test_end_to_end_candidates_adapts_without_db() -> None:
    rows = [
        track("a", genre="cinematic", energy=0.35, tempo=90.0),
        track("b", genre="cinematic", energy=0.65, tempo=110.0),
    ]

    result = end_to_end_candidates(rows)

    assert [item.intent_candidate.track_id for item in result] == ["a", "b"]
