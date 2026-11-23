import os
import io, json, os
import numpy as np

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

q = os.path.join(D, "p1_segmentation.json")
d = json.loads(io.open(q, encoding="utf-8").read())
print("p1_segmentation.json keys:", list(d.keys())[:20])
for k in list(d.keys())[:6]:
    v = d[k]
    print("  ", k, type(v).__name__, (list(v.keys())[:8] if isinstance(v, dict) else len(v) if hasattr(v, "__len__") else v))

z = np.load(os.path.join(D, "p1a_gpu_segmentation_probs.npz"), allow_pickle=True)
print("probs npz keys:", list(z.keys()))
for k in z.keys():
    print("  ", k, z[k].shape, z[k].dtype)

import pandas as pd
seg = pd.read_csv(os.path.join(D, "segments.csv"))
print("segments cols:", list(seg.columns), "rows", len(seg))
print(seg.head(3).to_string())