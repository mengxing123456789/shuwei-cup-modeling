# -*- coding: utf-8 -*-
"""探针：绕开 BLAS gemm，看哪些原语可用；并打印 numpy 配置。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np

print("numpy", np.__version__, flush=True)
try:
    np.show_config()
except Exception as e:
    print("show_config fail", e, flush=True)

A = np.random.rand(9, 3)
B = np.random.rand(3, 4)

def t(name, fn):
    try:
        r = fn()
        print(f"{name:16s} OK   {getattr(r, 'shape', type(r))}", flush=True)
    except Exception as e:
        print(f"{name:16s} RAISE {type(e).__name__}: {e}", flush=True)

t("einsum", lambda: np.einsum("ij,jk->ik", A, B))
t("einsum_t", lambda: np.einsum("ji,jk->ik", A, B))
t("inner", lambda: np.inner(A, B.T))
t("tensordot", lambda: np.tensordot(A, B, axes=([1], [0])))
t("sum_bcast", lambda: (A[:, :, None] * B[None, :, :]).sum(axis=1))
print("--- BLAS-dependent below (may kill process)", flush=True)
