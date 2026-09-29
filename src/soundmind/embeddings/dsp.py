import json
import numpy as np

class DSPEmbedder:
    name = "dsp-v1"
    dimension = 31

    def embed_from_row(self, row) -> np.ndarray:
        mfcc = tuple(json.loads(row.mfcc_json)) if row.mfcc_json else ()
        chroma = tuple(json.loads(row.chroma_json)) if row.chroma_json else ()
        values = [row.tempo_bpm, row.rms_energy, row.spectral_centroid,
                  row.spectral_bandwidth, row.spectral_rolloff,
                  row.zero_crossing_rate, *mfcc[:13], *chroma[:12]]
        vector = np.asarray([0.0 if x is None else float(x) for x in values], dtype=np.float32)
        if vector.size != self.dimension:
            raise ValueError(f"Expected {self.dimension} values, got {vector.size}")
        norm = float(np.linalg.norm(vector))
        return np.zeros_like(vector) if norm == 0 or not np.isfinite(norm) else vector / norm
