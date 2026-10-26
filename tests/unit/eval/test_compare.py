import json
import subprocess
from pathlib import Path

import pytest

from soundmind.evaluation import compare_reports


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "M19 Test"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "m19-test@example.invalid"], cwd=root, check=True
    )
    (root / ".gitignore").write_text("data/eval/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("synthetic compare fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "tracked.txt"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "synthetic compare fixture"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _report() -> dict:
    return {
        "dataset": "m19-queries",
        "dataset_version": "1.0.0",
        "query_dataset_sha256": "query-sha",
        "judgments_sha256": "judgments-sha",
        "catalog_fingerprint": "sha256:catalog",
        "current_catalog_fingerprint": "sha256:catalog",
        "catalog_fingerprint_status": "matched",
        "reproducibility": {"status": "reproducible", "reason": None},
        "selected_mode_status": "available",
        "code_revision": "synthetic-revision",
        "queries": [
            {"query_id": "q001", "status": "evaluable"},
            {"query_id": "q002", "status": "not_evaluable"},
        ],
        "summary": {
            "nDCG@10": {"value": 0.5},
            "Recall@10": {"value": 0.4},
            "MRR@10": {"value": 0.3},
        },
    }


def _write_reports(root: Path, baseline: dict, candidate: dict) -> tuple[Path, Path]:
    folder = root / "data" / "eval" / "reports"
    folder.mkdir(parents=True)
    baseline_path = folder / "baseline.json"
    candidate_path = folder / "candidate.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    return baseline_path.relative_to(root), candidate_path.relative_to(root)


def test_compare_reports_accepts_identical_evaluation_basis(tmp_path: Path, capsys) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    baseline = _report()
    candidate = _report()
    baseline_path, candidate_path = _write_reports(root, baseline, candidate)

    result = compare_reports(
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        repo_root=root,
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["metrics"]["nDCG@10"]["delta"] == 0.0


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("query_dataset_sha256", "different-query-sha", "query dataset content differs"),
        ("judgments_sha256", "different-judgments-sha", "judgment data or frozen-pool definition differs"),
        ("current_catalog_fingerprint", "sha256:other-catalog", "current catalog fingerprints differ"),
    ],
)
def test_compare_reports_rejects_different_evaluation_basis(
    tmp_path: Path, capsys, field: str, value: str, expected_error: str
) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    baseline = _report()
    candidate = _report()
    candidate[field] = value
    baseline_path, candidate_path = _write_reports(root, baseline, candidate)

    result = compare_reports(
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        repo_root=root,
    )

    assert result == 1
    assert expected_error in capsys.readouterr().err


def test_compare_reports_rejects_non_reproducible_report(tmp_path: Path, capsys) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    baseline = _report()
    candidate = _report()
    candidate["reproducibility"] = {
        "status": "non_reproducible",
        "reason": "synthetic stale catalog",
    }
    candidate["catalog_fingerprint_status"] = "mismatch"
    baseline_path, candidate_path = _write_reports(root, baseline, candidate)

    result = compare_reports(
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        repo_root=root,
    )

    assert result == 1
    assert "candidate is not reproducible" in capsys.readouterr().err


def test_compare_reports_rejects_changed_evaluable_query_set(tmp_path: Path, capsys) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    baseline = _report()
    candidate = _report()
    candidate["queries"][0]["status"] = "not_evaluable"
    baseline_path, candidate_path = _write_reports(root, baseline, candidate)

    result = compare_reports(
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        repo_root=root,
    )

    assert result == 1
    assert "evaluable query sets or per-query statuses differ" in capsys.readouterr().err
