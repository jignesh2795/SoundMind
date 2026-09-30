import os

import numpy as np
import pytest

from soundmind.vector.index import NumpyVectorIndex


def test_search(tmp_path):
    i = NumpyVectorIndex(tmp_path / "v", 2)
    i.save(["a", "b", "c"], np.asarray([[1, 0], [.9, .1], [-1, 0]], dtype=np.float32))
    r = i.search(np.asarray([1, 0], dtype=np.float32), limit=2)
    assert [x.track_id for x in r] == ["a", "b"]


def test_search_rejects_torn_publication(tmp_path):
    index = NumpyVectorIndex(tmp_path / "v", 2)
    index.save(["a"], np.asarray([[1, 0]], dtype=np.float32))

    replacement = NumpyVectorIndex(tmp_path / "replacement", 2)
    replacement.save(["b"], np.asarray([[0, 1]], dtype=np.float32))
    os.replace(replacement.vectors_path, index.vectors_path)
    stat = index.vectors_path.stat()
    os.utime(index.vectors_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    with pytest.raises(ValueError, match="integrity"):
        index.search(np.asarray([1, 0], dtype=np.float32))


def test_search_requires_integrity_metadata(tmp_path):
    index = NumpyVectorIndex(tmp_path / "v", 2)
    index.save(["a"], np.asarray([[1, 0]], dtype=np.float32))
    index.integrity_path.unlink()

    with pytest.raises(ValueError, match="integrity metadata"):
        index.search(np.asarray([1, 0], dtype=np.float32))
