from hashlib import sha256
from pathlib import Path

def stable_track_id(source_uri: str) -> str:
    return sha256(source_uri.encode("utf-8")).hexdigest()

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
