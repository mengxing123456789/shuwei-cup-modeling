#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""numlib —— 绕开 BLAS/LAPACK 的极小线性代数（本机实测约束，见 §环境）。

为什么需要这个文件
------------------
本机 `E:\\Mini\\envs\\mathmodel\\python.exe`（numpy 2.4.6）的 OpenBLAS 一碰
gemm/LAPACK 就整进程硬崩 `Windows fatal exception: code 0xc06d007f`，
`exit code -1066598273`。实测边界（每项独立进程跑，崩了就是崩了）：

    可用：einsum（optimize=False）、广播乘加求和、mean/std/percentile/quantile/
          median/sort/argsort/argmax/unique/clip/exp/log/sqrt/cumsum/sign/column_stack
    崩溃：A @ B、np.dot、np.inner、np.tensordot、np.einsum(optimize=True)、
          np.linalg.lstsq、np.linalg.solve、np.linalg.inv、np.linalg.svd、
          np.linalg.qr、np.polyfit

复算命令（任一崩 = 复现）：
    python code\\_probe_one.py matmul      # 崩
    python code\\_probe_one.py einsum      # 通
因此本工程**不许出现 @ / dot / lstsq / polyfit**，最小二乘一律走
`einsum` 组装正规方程 + 纯 Python 高斯消元。这同时保证了跨机器可移植
（纯 Python 消元不依赖任何 BLAS）。

精度说明：正规方程的 cond(AᵀA)=cond(A)²，本题设计矩阵只有 2 列
（[1, w]），cond ≈ 4，平方后仍在 1e1 量级，正规方程足够。若将来加高次项，
须改用 Householder QR（本文件已留 `qr_lstsq` 的位置，未实现）。
"""
from __future__ import annotations

import numpy as np

__all__ = ["solve_dense", "inv_dense", "lstsq", "matmul", "dotv", "cond_hint"]


def matmul(A, B):
    """A(m,k)·B(k,n) 用 einsum 实现（不触发 BLAS gemm）。"""
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    return np.einsum("ik,kj->ij", A, B)


def dotv(a, b):
    """向量点积（用乘加求和，不走 BLAS）。"""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float((a * b).sum())


def solve_dense(A, B):
    """解 A·X = B，A 为 n×n，B 为 n×m。部分主元高斯消元，纯 Python 循环。"""
    A = np.array(A, dtype=float, copy=True)
    B = np.array(B, dtype=float, copy=True)
    n = A.shape[0]
    if B.ndim == 1:
        B = B[:, None]
        squeeze = True
    else:
        squeeze = False
    for col in range(n):
        piv = int(np.argmax(np.abs(A[col:, col]))) + col
        if abs(A[piv, col]) < 1e-14:
            raise np.linalg.LinAlgError(f"矩阵奇异（列 {col} 主元 ~0）")
        if piv != col:
            A[[col, piv]] = A[[piv, col]]
            B[[col, piv]] = B[[piv, col]]
        pv = A[col, col]
        A[col] = A[col] / pv
        B[col] = B[col] / pv
        for r in range(n):
            if r == col:
                continue
            f = A[r, col]
            if f == 0.0:
                continue
            A[r] = A[r] - f * A[col]
            B[r] = B[r] - f * B[col]
    return B[:, 0] if squeeze else B


def inv_dense(A):
    A = np.asarray(A, dtype=float)
    n = A.shape[0]
    return solve_dense(A, np.eye(n))


def lstsq(X, Y):
    """最小二乘 B = argmin ||X·B - Y||，走正规方程 + 纯 Python 消元。

    返回 (B, rss)。X (n,k)，Y (n,) 或 (n,m)。
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    one_d = Y.ndim == 1
    if one_d:
        Y = Y[:, None]
    XtX = np.einsum("ni,nj->ij", X, X)
    XtY = np.einsum("ni,nm->im", X, Y)
    B = solve_dense(XtX, XtY)
    R = Y - np.einsum("nk,km->nm", X, B)
    rss = float((R * R).sum())
    return (B[:, 0] if one_d else B), rss


def cond_hint(X) -> float:
    """设计矩阵条件数的粗略指标（||X||₁·||X⁺||₁ 不可算时用列范数比）。"""
    X = np.asarray(X, dtype=float)
    norms = np.sqrt((X * X).sum(axis=0))
    return float(norms.max() / max(norms.min(), 1e-300))
