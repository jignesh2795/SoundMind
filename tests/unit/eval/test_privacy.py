import subprocess
from pathlib import Path

from soundmind.evaluation import (
    PrivacyGateError,
    enforce_privacy_gate,
    run_evaluation,
)


def _init_repo(root: Path, *, ignore_eval: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "M19 Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "m19-test@example.invalid"], cwd=root, check=True)
    empty_excludes = root / "empty-excludes"
    empty_excludes.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "config", "core.excludesFile", str(empty_excludes)], cwd=root, check=True
    )
    ignores = "data/database/\n" + ("data/eval/\n" if ignore_eval else "")
    (root / ".gitignore").write_text(ignores, encoding="utf-8")
    (root / "tracked.txt").write_text("synthetic test repository\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "test fixture"], cwd=root, check=True,
                   capture_output=True, text=True)
    return root


def test_privacy_gate_accepts_both_canonical_paths_and_custom_local_paths(tmp_path: Path) -> None:
    root = _init_repo(tmp_path / "repo")
    actual_root, judgments, report = enforce_privacy_gate(
        repo_root=root,
        judgments_path=Path("data/eval/judgments.local.json"),
        output_path=Path("data/eval/reports/synthetic-report.json"),
    )
    assert actual_root == root.resolve()
    assert judgments == root / "data/eval/judgments.local.json"
    assert report == root / "data/eval/reports/synthetic-report.json"
    assert not report.parent.exists()


def test_privacy_gate_rejects_custom_path_outside_eval(tmp_path: Path) -> None:
    root = _init_repo(tmp_path / "repo")
    try:
        enforce_privacy_gate(
            repo_root=root,
            judgments_path=Path("data/eval/judgments.local.json"),
            output_path=root / "leak.json",
        )
    except PrivacyGateError as exc:
        assert "inside data/eval" in str(exc)
    else:
        raise AssertionError("outside path should have been rejected")


def test_run_aborts_before_creating_output_when_ignore_rule_is_missing(
    tmp_path: Path, capsys
) -> None:
    root = _init_repo(tmp_path / "repo", ignore_eval=False)
    out = root / "data/eval/reports/baseline-report.json"
    result = run_evaluation(
        repo_root=root,
        dataset_path=root / "missing-query-dataset.json",
        judgments_path=Path("data/eval/judgments.local.json"),
        output_path=Path("data/eval/reports/baseline-report.json"),
        database_path=Path("data/database/soundmind.db"),
    )
    assert result == 2
    assert not out.parent.exists()
    assert "privacy gate blocked" in capsys.readouterr().err
