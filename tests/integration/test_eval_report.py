import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from soundmind.evaluation import (
    REQUIRED_LIMITATIONS_BLOCK,
    build_frozen_pool,
    run_evaluation,
)
from soundmind.storage.database import Base
from soundmind.storage.models import TrackRow


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "M19 Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "m19-test@example.invalid"], cwd=root, check=True)
    empty_excludes = root / "empty-excludes"
    empty_excludes.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "config", "core.excludesFile", str(empty_excludes)], cwd=root, check=True
    )
    (root / ".gitignore").write_text("data/eval/\ndata/database/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("synthetic integration fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "synthetic test fixture"], cwd=root, check=True,
                   capture_output=True, text=True)


def _make_track(track_id: str, index: int, genre: str, energy: float) -> TrackRow:
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    return TrackRow(
        track_id=track_id,
        content_hash=f"{index:064x}",
        source_type="file",
        source_uri=f"file:///synthetic/{track_id}.mp3",
        file_name=f"{track_id}.mp3",
        file_size=1,
        modified_at_ns=index + 1,
        status="active",
        created_at=stamp,
        updated_at=stamp,
        title=f"Synthetic title {index}",
        artist="Synthetic artist",
        album="Synthetic album",
        genre=genre,
        rms_energy=energy,
        tempo_bpm=100.0 + index,
    )


def test_eval_report_runs_read_only_and_contains_contract_fields(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)

    dataset_path = root / "datasets/m19/queries-v1.json"
    dataset_path.parent.mkdir(parents=True)
    query_doc = {
        "dataset": "m19-queries",
        "version": "1.0.0",
        "queries": [{
            "id": "q001",
            "text": "high energy cinematic instrumental",
            "facets": {"genre": ["cinematic"], "energy": "high"},
            "notes": "synthetic fixture only",
        }],
    }
    dataset_path.write_text(json.dumps(query_doc), encoding="utf-8")

    track_ids = ["synthetic-track-a", "synthetic-track-b", "synthetic-track-c"]
    pool = build_frozen_pool(
        {"catalog": track_ids}, {"catalog": 10}, dataset_version="1.0.0"
    )
    judgment_doc = {
        "dataset": "m19-queries",
        "dataset_version": "1.0.0",
        "catalog_fingerprint": "synthetic-fixture-not-a-real-catalog",
        "judged_at": "2026-10-26T00:00:00Z",
        "pool_manifest": {"dataset_version": "1.0.0", "queries": {"q001": pool}},
        "judgments": [
            {"query_id": "q001", "track_id": track_ids[0], "grade": 3,
             "reason": "Synthetic strong match"},
            {"query_id": "q001", "track_id": track_ids[1], "grade": 2,
             "reason": "Synthetic relevant result"},
            {"query_id": "q001", "track_id": track_ids[2], "grade": 0,
             "reason": "Synthetic known mismatch"},
        ],
    }
    judgment_path = root / "data/eval/judgments.local.json"
    judgment_path.parent.mkdir(parents=True)
    judgment_path.write_text(json.dumps(judgment_doc), encoding="utf-8")

    database_path = root / "data/database/soundmind.db"
    database_path.parent.mkdir(parents=True)
    write_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(write_engine)
    factory = sessionmaker(write_engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            _make_track(track_ids[0], 1, "cinematic", 0.95),
            _make_track(track_ids[1], 2, "cinematic", 0.75),
            _make_track(track_ids[2], 3, "ambient", 0.25),
        ])
        session.commit()
    write_engine.dispose()
    before_hash = hashlib.sha256(database_path.read_bytes()).hexdigest()

    report_path = Path("data/eval/reports/baseline-report.json")
    result = run_evaluation(
        repo_root=root,
        dataset_path=dataset_path,
        judgments_path=Path("data/eval/judgments.local.json"),
        retrieval="catalog",
        limit=10,
        output_path=report_path,
        database_path=Path("data/database/soundmind.db"),
    )

    assert result == 0
    report_file = root / report_path
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["selected_mode_status"] == "available"
    assert report["queries"][0]["status"] == "evaluable"
    assert report["queries"][0]["pool_coverage"] == 1.0
    assert report["summary"]["nDCG@10"]["value"] is not None
    assert report["summary"]["Recall@10"]["value"] == 1.0
    assert report["summary"]["MRR@10"]["value"] is not None
    assert report["limitations"] == REQUIRED_LIMITATIONS_BLOCK
    assert report["mode_availability"]["semantic"]["status"] in {"available", "unavailable"}
    after_hash = hashlib.sha256(database_path.read_bytes()).hexdigest()
    assert after_hash == before_hash
