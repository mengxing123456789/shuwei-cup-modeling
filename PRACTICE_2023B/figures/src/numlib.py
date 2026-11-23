#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""numlib \u2014\u2014 \u7ed5\u5f00 BLAS/LAPACK \u7684\u6781\u5c0f\u7ebf\u6027\u4ee3\u6570\uff08\u672c\u673a\u5b9e\u6d4b\u7ea6\u675f\uff0c\u89c1 \u00a7\u73af\u5883\uff09\u3002

\u4e3a\u4ec0\u4e48\u9700\u8981\u8fd9\u4e2a\u6587\u4ef6
------------------
\u672c\u673a `E:\\Mini\\envs\\mathmodel\\python.exe`\uff08numpy 2.4.6\uff09\u7684 OpenBLAS \u4e00\u78b0
gemm/LAPACK \u5c31\u6574\u8fdb\u7a0b\u786c\u5d29 `Windows fatal exception: code 0xc06d007f`\uff0c
`exit code -1066598273`\u3002\u5b9e\u6d4b\u8fb9\u754c\uff08\u6bcf\u9879\u72ec\u7acb\u8fdb\u7a0b\u8dd1\uff0c\u5d29\u4e86\u5c31\u662f\u5d29\u4e86\uff09\uff1a

    \u53ef\u7528\uff1aeinsum\uff08optimize=False\uff09\u3001\u5e7f\u64ad\u4e58\u52a0\u6c42\u548c\u3001mean/std/percentile/quantile/
          median/sort/argsort/argmax/unique/clip/exp/log/sqrt/cumsum/sign/column_stack
    \u5d29\u6e83\uff1aA @ B\u3001np.dot\u3001np.inner\u3001np.tensordot\u3001np.einsum(optimize=True)\u3001
          np.linalg.lstsq\u3001np.linalg.solve\u3001np.linalg.inv\u3001np.linalg.svd\u3001
          np.linalg.qr\u3001np.polyfit

\u590d\u7b97\u547d\u4ee4\uff08\u4efb\u4e00\u5d29 = \u590d\u73b0\uff09\uff1a
    python code\\_probe_one.py matmul      # \u5d29
    python code\\_probe_one.py einsum      # \u901a
\u56e0\u6b64\u672c\u5de5\u7a0b**\u4e0d\u8bb8\u51fa\u73b0 @ / dot / lstsq / polyfit**\uff0c\u6700\u5c0f\u4e8c\u4e58\u4e00\u5f8b\u8d70
`einsum` \u7ec4\u88c5\u6b63\u89c4\u65b9\u7a0b + \u7eaf Python \u9ad8\u65af\u6d88\u5143\u3002\u8fd9\u540c\u65f6\u4fdd\u8bc1\u4e86\u8de8\u673a\u5668\u53ef\u79fb\u690d
\uff08\u7eaf Python \u6d88\u5143\u4e0d\u4f9d\u8d56\u4efb\u4f55 BLAS\uff09\u3002

\u7cbe\u5ea6\u8bf4\u660e\uff1a\u6b63\u89c4\u65b9\u7a0b\u7684 cond(A\u1d40A)=cond(A)\u00b2\uff0c\u672c\u9898\u8bbe\u8ba1\u77e9\u9635\u53ea\u6709 2 \u5217
\uff08[1, w]\uff09\uff0ccond \u2248 4\uff0c\u5e73\u65b9\u540e\u4ecd\u5728 1e1 \u91cf\u7ea7\uff0c\u6b63\u89c4\u65b9\u7a0b\u8db3\u591f\u3002\u82e5\u5c06\u6765\u52a0\u9ad8\u6b21\u9879\uff0c
\u987b\u6539\u7528 Householder QR\uff08\u672c\u6587\u4ef6\u5df2\u7559 `qr_lstsq` \u7684\u4f4d\u7f6e\uff0c\u672a\u5b9e\u73b0\uff09\u3002
"""
from __future__ import annotations

import numpy as np

__all__ = ["solve_dense", "inv_dense", "lstsq", "matmul", "dotv", "cond_hint"]


def matmul(A, B):
    """A(m,k)\u00b7B(k,n) \u7528 einsum \u5b9e\u73b0\uff08\u4e0d\u89e6\u53d1 BLAS gemm\uff09\u3002"""
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    return np.einsum("ik,kj->ij", A, B)


def dotv(a, b):
    """\u5411\u91cf\u70b9\u79ef\uff08\u7528\u4e58\u52a0\u6c42\u548c\uff0c\u4e0d\u8d70 BLAS\uff09\u3002"""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float((a * b).sum())


def solve_dense(A, B):
    """\u89e3 A\u00b7X = B\uff0cA \u4e3a n\u00d7n\uff0cB \u4e3a n\u00d7m\u3002\u90e8\u5206\u4e3b\u5143\u9ad8\u65af\u6d88\u5143\uff0c\u7eaf Python \u5faa\u73af\u3002"""
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
            raise np.linalg.LinAlgError(f"\u77e9\u9635\u5947\u5f02\uff08\u5217 {col} \u4e3b\u5143 ~0\uff09")
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
    """\u6700\u5c0f\u4e8c\u4e58 B = argmin ||X\u00b7B - Y||\uff0c\u8d70\u6b63\u89c4\u65b9\u7a0b + \u7eaf Python \u6d88\u5143\u3002

    \u8fd4\u56de (B, rss)\u3002X (n,k)\uff0cY (n,) \u6216 (n,m)\u3002
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
    """\u8bbe\u8ba1\u77e9\u9635\u6761\u4ef6\u6570\u7684\u7c97\u7565\u6307\u6807\uff08||X||\u2081\u00b7||X\u207a||\u2081 \u4e0d\u53ef\u7b97\u65f6\u7528\u5217\u8303\u6570\u6bd4\uff09\u3002"""
    X = np.asarray(X, dtype=float)
    norms = np.sqrt((X * X).sum(axis=0))
    return float(norms.max() / max(norms.min(), 1e-300))
