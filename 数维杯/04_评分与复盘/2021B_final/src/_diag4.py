# -*- coding: utf-8 -*-
import os
print("OPENBLAS_NUM_THREADS=", os.environ.get("OPENBLAS_NUM_THREADS"), flush=True)
import numpy as np, pandas as pd, sys
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
print("numpy", np.__version__, flush=True)
a = np.random.default_rng(0).normal(size=17085)
b = np.random.default_rng(1).normal(size=17085)
print("corrcoef random", flush=True)
print(np.corrcoef(a, b)[0, 1], flush=True)
print("lstsq", flush=True)
X = np.column_stack([np.ones_like(a), a])
print(np.linalg.lstsq(X, b, rcond=None)[0], flush=True)
print("polyfit", np.polyfit(a, b, 2)[0], flush=True)