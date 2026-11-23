# -*- coding: utf-8 -*-
"""逐个原语在独立进程里试，定位本机 BLAS 崩溃边界。

用法：python _probe_one.py <name>
每个 name 单独跑一次，进程崩了就是崩了（exit code 非 0）。
"""
import sys
import numpy as np

name = sys.argv[1]
A = np.random.rand(9, 3)
B = np.random.rand(3, 4)
X = np.random.rand(9, 2)
y = np.random.rand(9, 3)

if name == "einsum":
    r = np.einsum("ij,jk->ik", A, B)
elif name == "einsum_opt":
    r = np.einsum("ij,jk->ik", A, B, optimize=True)
elif name == "einsum_3d":
    r = np.einsum("nj,jk->nk", X, np.random.rand(2, 3))
elif name == "matmul":
    r = A @ B
elif name == "dot":
    r = np.dot(A, B)
elif name == "inner":
    r = np.inner(A, B.T)
elif name == "tensordot":
    r = np.tensordot(A, B, axes=([1], [0]))
elif name == "bcast_sum":
    r = (A[:, :, None] * B[None, :, :]).sum(axis=1)
elif name == "lstsq":
    r = np.linalg.lstsq(X, y, rcond=None)[0]
elif name == "solve":
    r = np.linalg.solve(X.T @ X if False else np.eye(2), np.eye(2))
elif name == "inv":
    r = np.linalg.inv(np.eye(3) * 2)
elif name == "svd":
    r = np.linalg.svd(A, full_matrices=False)[1]
elif name == "qr":
    r = np.linalg.qr(A)[0]
elif name == "polyfit":
    r = np.polyfit(np.arange(9.0), y[:, 0], 1)
elif name == "mean":
    r = y.mean(axis=0)
elif name == "cumsum":
    r = np.cumsum(y, axis=0)
else:
    raise SystemExit("unknown " + name)

print("OK", name, np.shape(r), flush=True)
