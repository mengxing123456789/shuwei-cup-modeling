# -*- coding: utf-8 -*-
"""逐个原语在独立进程里试（第二批：非 BLAS 的常用函数）。"""
import sys
import numpy as np

name = sys.argv[1]
A = np.random.rand(9, 3) + 0.5
v = np.array([0.3, -0.7, 1.2, 0.05])

if name == "percentile":
    r = np.percentile(A, 5, axis=0)
elif name == "sort":
    r = np.sort(A, axis=0)
elif name == "argsort":
    r = np.argsort(A[:, 0])
elif name == "log_exp":
    r = np.exp(np.log(A))
elif name == "sqrt_abs":
    r = np.sqrt(np.abs(v))
elif name == "argmax":
    r = np.argmax(A[:, 0])
elif name == "column_stack":
    r = np.column_stack([A, A[:, :1]])
elif name == "diff_sign":
    r = np.sign(np.diff(v))
elif name == "norm":
    r = np.linalg.norm(v)
elif name == "norm_manual":
    r = np.sqrt((v * v).sum())
elif name == "std":
    r = A.std(axis=0)
elif name == "quantile":
    r = np.quantile(A, 0.95, axis=0)
elif name == "median":
    r = np.median(A, axis=0)
elif name == "unique":
    r = np.unique(np.round(v, 1))
elif name == "lstsq_manual":
    X = np.column_stack([np.ones(9), np.arange(9.0)])
    XtX = np.einsum("ni,nj->ij", X, X)
    XtY = np.einsum("ni,nj->ij", X, A)
    r = XtX, XtY
elif name == "einsum_ij":
    r = np.einsum("ni,nj->ij", A, A)
elif name == "clip":
    r = np.clip(v, -0.5, 0.5)
elif name == "polyval":
    r = np.polyval([1.0, 2.0], np.arange(3.0))
else:
    raise SystemExit("unknown " + name)

print("OK", name, np.shape(r), flush=True)
