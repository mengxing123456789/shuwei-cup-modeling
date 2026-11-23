# -*- coding: utf-8 -*-
"""探针：numpy 的 @ / dot 在本机是否崩（0xc06d007f）。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np

print("numpy", np.__version__, flush=True)
A = np.random.rand(9, 3)
B = np.random.rand(3, 4)
print("einsum", np.einsum("ij,jk->ik", A, B).shape, flush=True)
try:
    C = A @ B
    print("matmul ok", C.shape, flush=True)
except Exception as e:
    print("matmul raise", e, flush=True)
print("dot", np.dot(A, B).shape, flush=True)
print("lstsq", np.linalg.lstsq(np.random.rand(9, 2), A, rcond=None)[0].shape, flush=True)
print("svd", np.linalg.svd(A, full_matrices=False)[1].shape, flush=True)
