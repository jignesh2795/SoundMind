from pathlib import Path
import argparse
from soundmind.config import AnalysisConfig
from soundmind.embeddings.effnet import EffNetConfig, EffNetEmbedder
from soundmind.embeddings.learned_service import LearnedEmbeddingService
from soundmind.embeddings.effnet import fetch_effnet_model
from soundmind.storage.database import create_session_factory

def build_parser():
    p=argparse.ArgumentParser(prog="soundmind"); s=p.add_subparsers(dest="command",required=True)
    m=s.add_parser("model"); ms=m.add_subparsers(dest="model_command",required=True)
    f=ms.add_parser("fetch-effnet"); f.add_argument("--path",type=Path,default=Path("data/models/discogs-effnet-bsdynamic-1.onnx"))
    li=s.add_parser("learned-index"); ls=li.add_subparsers(dest="learned_command",required=True)
    r=ls.add_parser("rebuild"); r.add_argument("--db",type=Path,default=Path("data/database/soundmind.db")); r.add_argument("--model",type=Path,default=Path("data/models/discogs-effnet-bsdynamic-1.onnx")); r.add_argument("--index",type=Path,default=Path("data/index/effnet_vectors")); r.add_argument("--limit",type=int)
    q=ls.add_parser("similar"); q.add_argument("track_id"); q.add_argument("--db",type=Path,default=Path("data/database/soundmind.db")); q.add_argument("--model",type=Path,default=Path("data/models/discogs-effnet-bsdynamic-1.onnx")); q.add_argument("--index",type=Path,default=Path("data/index/effnet_vectors")); q.add_argument("--limit",type=int,default=10)
    return p

def main():
    a=build_parser().parse_args()
    if a.command=="model":
        print(fetch_effnet_model(a.path)); return 0
    if a.command=="learned-index":
        sf=create_session_factory(a.db)
        with sf() as session:
            svc=LearnedEmbeddingService(session,model_path=a.model,index_path=a.index)
            if a.learned_command=="rebuild": print(f"Indexed learned embeddings: {svc.rebuild(limit=a.limit)}"); return 0
            for x in svc.similar(a.track_id,limit=a.limit): print(f"{x.track_id}\t{x.score:.6f}")
            return 0
    return 1

if __name__=="__main__": raise SystemExit(main())
