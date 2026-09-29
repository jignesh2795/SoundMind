from pathlib import Path

from soundmind.diagnostics import ProcessingIssue
from soundmind.ingestion.metadata import extract_metadata


def test_metadata_failure_is_reported_without_raising(tmp_path: Path):
    path = tmp_path / "broken.mp3"
    path.write_bytes(b"not-audio")
    diagnostics: list[ProcessingIssue] = []

    result = extract_metadata(path, diagnostics=diagnostics)

    assert result.duration_seconds is None
    assert len(diagnostics) == 1
    assert diagnostics[0].stage == "metadata"
    assert diagnostics[0].source == str(path)
    assert diagnostics[0].error_type


def test_processing_issue_is_immutable():
    issue = ProcessingIssue("analysis", "song.mp3", "RuntimeError", "failed")
    assert issue.stage == "analysis"
    assert issue.source == "song.mp3"
