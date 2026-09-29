import numpy as np

from soundmind.vector.index import NumpyVectorIndex


def test_search(tmp_path):
    i=NumpyVectorIndex(tmp_path/"v",2)
    i.save(["a","b","c"],np.asarray([[1,0],[.9,.1],[-1,0]],dtype=np.float32))
    r=i.search(np.asarray([1,0],dtype=np.float32),limit=2)
    assert [x.track_id for x in r]==["a","b"]
