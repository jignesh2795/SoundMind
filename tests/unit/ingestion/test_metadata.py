from pathlib import Path
from soundmind.ingestion.metadata import AudioMetadata, extract_metadata

def test_missing_or_unsupported_metadata_is_safe(tmp_path: Path):
    path = tmp_path / "empty.mp3"
    path.write_bytes(b"not-a-real-audio-file")
    assert extract_metadata(path) == AudioMetadata()
