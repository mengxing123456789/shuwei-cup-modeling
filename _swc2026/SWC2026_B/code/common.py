# -*- coding: utf-8 -*-
"""SWC2026 B 公共几何 / 时序库。

全部单位：米、秒、度（除非显式写 rad）。
坐标系：原点在场地西南角，x 向东，y 向北；方位角自正东逆时针。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import sys

import numpy as np

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WS, "data")
FIG = os.path.join(WS, "figures")
PROBLEM = os.path.join(WS, "problem", "problem.txt")

os.makedirs(DATA, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

# ---------------- 题给常量（出处见 out/00-problem.md） ----------------
# (id, x0, x1, y0, y1, h)
BUILDINGS = [
    ("B1", 22.0, 34.0, 16.0, 26.0, 20.0),
    ("B2", 63.0, 79.0, 59.0, 71.0, 28.0),
    ("B3", 10.0, 24.0, 65.0, 76.0, 12.0),
    ("B4", 72.0, 86.0, 22.0, 34.0, 24.0),
    ("B5", 41.0, 51.0, 38.0, 46.0, 32.0),
]
VEH0 = {
    "V1": (15.0, 14.0),
    "V2": (88.0, 10.0),
    "V3": (14.0, 86.0),
    "V4": (88.0, 68.0),
    "V5": (50.0, 93.0),
}
# (theta deg, R m, H m)
TARGETS = {
    "T1": (30.0, 40.0, 45.0),
    "T2": (150.0, 45.0, 35.0),
    "T3": (285.0, 38.0, 55.0),
}
O = np.array([50.0, 50.0])
FIELD = (0.0, 100.0)

CAM_Z = 2.0
VEH_R = 1.5
SPEED = 3.0
ELEV_MIN, ELEV_MAX = -10.0, 80.0
RATE = 30.0          # deg/s，pan/tilt 同一上限
T_OBS = 5.0

SIGMA_DEG = 1.0      # P2 测角标准差
SIGMA_RAD = math.radians(SIGMA_DEG)


# ---------------- 基础量 ----------------
def target_xyz(name: str) -> np.ndarray:
    th, R, H = TARGETS[name]
    th = math.radians(th)
    return np.array([O[0] + R * math.cos(th), O[1] + R * math.sin(th), H])


def target_xy(name: str) -> np.ndarray:
    return target_xyz(name)[:2]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def meta(script: str) -> dict:
    return {
        "script": script,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "problem_sha256": sha256_file(PROBLEM),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
    }


def dump(name: str, obj: dict):
    """所有数字唯一出口：data/<name>.json，UTF-8 无 BOM，缩进 2。"""
    p = os.path.join(DATA, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"[dump] {p}  {os.path.getsize(p)} B")


# ---------------- 线段 / 矩形 相交 ----------------
def seg_rect_hit(ax, ay, bx, by, rect, eps=0.0):
    """2D 线段 A->B 与闭矩形相交（含相切）。rect=(x0,x1,y0,y1)。A 可为标量、B 可为数组。"""
    ax = np.asarray(ax, dtype=float)
    ay = np.asarray(ay, dtype=float)
    bx = np.asarray(bx, dtype=float)
    by = np.asarray(by, dtype=float)
    x0, x1, y0, y1 = rect
    tmin = np.zeros(np.broadcast(ax, bx).shape)
    tmax = np.ones(np.broadcast(ax, bx).shape)
    for p, b, lo, hi in ((ax, bx, x0 - eps, x1 + eps), (ay, by, y0 - eps, y1 + eps)):
        d = b - p
        par = np.abs(d) < 1e-12
        outside = par & ((p < lo) | (p > hi))
        dsafe = np.where(par, 1.0, d)
        t1 = (lo - p) / dsafe
        t2 = (hi - p) / dsafe
        tlo = np.minimum(t1, t2)
        thi = np.maximum(t1, t2)
        tmin = np.maximum(tmin, np.where(par, -np.inf, tlo))
        tmax = np.minimum(tmax, np.where(par, np.inf, thi))
        tmin = np.where(outside, np.inf, tmin)
    return (tmin <= tmax) & (tmin <= 1.0) & (tmax >= 0.0)


def seg_aabb_hit(p0, p1, lo, hi, eps=1e-9):
    """3D 线段与闭 AABB 相交（slab 法）。p0:(N,3) 或 (3,)，p1:(3,) 或 (N,3)。"""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p0, p1 = np.broadcast_arrays(p0, p1)
    d = p1 - p0
    shape = d.shape[:-1]
    tmin = np.zeros(shape)
    tmax = np.ones(shape)
    for k in range(3):
        pk, dk = p0[..., k], d[..., k]
        lo_k, hi_k = lo[k] - eps, hi[k] + eps
        par = np.abs(dk) < 1e-12
        outside = par & ((pk < lo_k) | (pk > hi_k))
        dsafe = np.where(par, 1.0, dk)
        t1 = (lo_k - pk) / dsafe
        t2 = (hi_k - pk) / dsafe
        tlo = np.minimum(t1, t2)
        thi = np.maximum(t1, t2)
        tmin = np.maximum(tmin, np.where(par, -np.inf, tlo))
        tmax = np.minimum(tmax, np.where(par, np.inf, thi))
        tmin = np.where(outside, np.inf, tmin)
    return (tmin <= tmax) & (tmin <= 1.0) & (tmax >= 0.0)


# ---------------- 可观测性 ----------------
def point_rect_dist(x, y, b):
    """点到闭矩形的最短距离（矩形内为 0）。"""
    _, x0, x1, y0, y1, _ = b
    dx = np.maximum(np.maximum(x0 - x, x - x1), 0.0)
    dy = np.maximum(np.maximum(y0 - y, y - y1), 0.0)
    return np.hypot(dx, dy)


def geom_ok(x, y, margin=VEH_R):
    """车体（半径 margin 的圆盘）在场地内且不进楼。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = (x >= margin) & (x <= FIELD[1] - margin) & (y >= margin) & (y <= FIELD[1] - margin)
    for b in BUILDINGS:
        ok &= point_rect_dist(x, y, b) >= margin - 1e-12
    return ok


def elev_deg(x, y, name):
    t = target_xyz(name)
    r = np.hypot(t[0] - np.asarray(x, float), t[1] - np.asarray(y, float))
    return np.degrees(np.arctan2(t[2] - CAM_Z, r))


def elev_ok(x, y, name):
    e = elev_deg(x, y, name)
    return (e >= ELEV_MIN - 1e-12) & (e <= ELEV_MAX + 1e-12)


def los_blocked(x, y, name, eps=1e-9):
    """三维视线是否被任一楼体遮挡（相切算遮挡）。"""
    t = target_xyz(name)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    p0 = np.stack([x, y, np.full(x.shape, CAM_Z)], axis=-1)
    p1 = t
    hit = np.zeros(x.shape, dtype=bool)
    for b in BUILDINGS:
        _, x0, x1, y0, y1, h = b
        hit = hit | seg_aabb_hit(p0, p1, np.array([x0, y0, 0.0]), np.array([x1, y1, h]), eps=eps)
    return hit


def planar_blocked(x, y, name):
    """平面阴影模型：楼体视为无限高墙，2D 视线穿过即遮挡。"""
    t = target_xyz(name)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    hit = np.zeros(x.shape, dtype=bool)
    for b in BUILDINGS:
        _, x0, x1, y0, y1, _ = b
        hit |= seg_rect_hit(x, y, t[0], t[1], (x0, x1, y0, y1), eps=0.0)
    return hit


def grid(ds=1.0):
    """格心网格。返回 xs (nx,), ys (ny,), X (ny,nx), Y (ny,nx)。"""
    n = int(round(FIELD[1] / ds))
    xs = (np.arange(n) + 0.5) * ds
    ys = xs.copy()
    X, Y = np.meshgrid(xs, ys)
    return xs, ys, X, Y


def observability(name, ds=1.0, mode="3d"):
    """返回 dict：各约束掩码与可观测掩码（栅格按 [iy, ix]）。"""
    xs, ys, X, Y = grid(ds)
    g = geom_ok(X, Y)
    e = elev_ok(X, Y, name)
    if mode == "3d":
        b = los_blocked(X, Y, name)
    elif mode == "planar":
        b = planar_blocked(X, Y, name)
    else:
        raise ValueError(mode)
    obs = g & e & (~b)
    return dict(xs=xs, ys=ys, X=X, Y=Y, geom=g, elev=e, blocked=b, obs=obs)


# ---------------- 绕障最短路（车心可行域 = 场地内缩 1.5，楼体外扩 1.5） ----------------
INFLATE = VEH_R
RECT_INF = [(b[1] - INFLATE, b[2] + INFLATE, b[3] - INFLATE, b[4] + INFLATE) for b in BUILDINGS]
CORNERS = np.array(
    sorted(
        {
            (round(x, 6), round(y, 6))
            for (x0, x1, y0, y1) in RECT_INF
            for x in (x0, x1)
            for y in (y0, y1)
            if VEH_R <= x <= FIELD[1] - VEH_R and VEH_R <= y <= FIELD[1] - VEH_R
        }
    )
)


def visible(p, q, eps=-1e-9):
    """车心从 p 到 q 的直线段是否无遮挡（eps<0：允许贴边）。"""
    for (x0, x1, y0, y1) in RECT_INF:
        if seg_rect_hit(p[0], p[1], q[0], q[1], (x0, x1, y0, y1), eps=eps):
            return False
    return True


def path_len(p, q, eps=-1e-9):
    """可见图 Dijkstra。节点 = p, q, 各外扩矩形角点。"""
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    nodes = np.vstack([p, q, CORNERS])
    n = len(nodes)
    dist = np.full(n, np.inf)
    done = np.zeros(n, bool)
    dist[0] = 0.0
    for _ in range(n):
        cand = np.where(~done, dist, np.inf)
        i = int(np.argmin(cand))
        if not np.isfinite(cand[i]):
            break
        done[i] = True
        if i == 1:
            break
        for j in range(n):
            if done[j]:
                continue
            w = float(np.hypot(*(nodes[j] - nodes[i])))
            if dist[i] + w < dist[j] - 1e-12 and visible(nodes[i], nodes[j], eps):
                dist[j] = dist[i] + w
    return float(dist[1])


def travel_time(p, q):
    return path_len(p, q) / SPEED


def travel_est_cells(p0, cells):
    """从 p0 到一批格心的近似最短路长度（一折点精确；多折点给出上界）。向量化。"""
    p0 = np.asarray(p0, float)
    cells = np.asarray(cells, float)
    d = np.hypot(cells[:, 0] - p0[0], cells[:, 1] - p0[1]).copy()
    blocked = np.zeros(len(cells), dtype=bool)
    for (x0, x1, y0, y1) in RECT_INF:
        blocked |= seg_rect_hit(p0[0], p0[1], cells[:, 0], cells[:, 1], (x0, x1, y0, y1), eps=-1e-9)
    if blocked.any():
        best = np.full(len(cells), np.inf)
        for c in CORNERS:
            if not visible(p0, c):
                continue
            dc = float(np.hypot(c[0] - p0[0], c[1] - p0[1]))
            hit = np.zeros(len(cells), dtype=bool)
            for (x0, x1, y0, y1) in RECT_INF:
                hit |= seg_rect_hit(c[0], c[1], cells[:, 0], cells[:, 1], (x0, x1, y0, y1), eps=-1e-9)
            cand = np.where(hit, np.inf, dc + np.hypot(cells[:, 0] - c[0], cells[:, 1] - c[1]))
            best = np.minimum(best, cand)
        d = np.where(blocked, np.minimum(best, np.inf), d)
    return d


# ---------------- 云台 / 时序 ----------------
def wrap180(a):
    """角度差折到 (-180, 180]。"""
    a = np.asarray(a, float)
    return (a + 180.0) % 360.0 - 180.0


def bearing_deg(p, q):
    """从 p 指向 q 的方位角，[0,360)。"""
    return float(np.degrees(np.arctan2(q[1] - p[1], q[0] - p[0])) % 360.0)


def slew_time(pan_from, tilt_from, pan_to, tilt_to):
    """两轴同时转，时长取较长者。角度单位度。"""
    dp = abs(float(wrap180(pan_to - pan_from)))
    dt = abs(float(tilt_to - tilt_from))
    return max(dp, dt) / RATE


def mission_from_station(station, name, t_free):
    """车已停在 station（云台正东水平）→ 指向 + 观测 + 复位。
    返回 (obs_start, obs_end, reset_end, pan, elev)。"""
    t = target_xyz(name)
    st = np.asarray(station, float)
    pan = bearing_deg(st, t[:2])
    elev = float(elev_deg(st[0], st[1], name))
    sl = slew_time(0.0, 0.0, pan, elev)
    obs_start = t_free + sl
    obs_end = obs_start + T_OBS
    reset = slew_time(pan, elev, 0.0, 0.0)
    return obs_start, obs_end, obs_end + reset, pan, elev


def mission_end_state(station, name, obs_end):
    """观测结束后复位到正东水平，返回可再出发时刻。"""
    t = target_xyz(name)
    st = np.asarray(station, float)
    pan = bearing_deg(st, t[:2])
    elev = float(elev_deg(st[0], st[1], name))
    reset = slew_time(pan, elev, 0.0, 0.0)
    return obs_end + reset


# ---------------- P2(1) 精度模型 ----------------
def drms_pair(s1, s2, name, sigma_deg=SIGMA_DEG):
    """两站方位交会的位置误差（DRMS）。

    观测方程线性化：n_i^T dp = r_i * dtheta_i，dtheta_i ~ N(0, sigma^2)。
    故 Cov(p) = A^{-1} diag(sigma^2 r1^2, sigma^2 r2^2) A^{-T}，A 的行是 n_i。
    闭式：DRMS = sigma * sqrt(r1^2 + r2^2) / |sin gamma|；gamma -> 0/180 时退化。
    """
    sig = math.radians(sigma_deg)
    t = target_xyz(name)[:2]
    s1 = np.asarray(s1, float)
    s2 = np.asarray(s2, float)
    a1 = math.atan2(t[1] - s1[1], t[0] - s1[0])
    a2 = math.atan2(t[1] - s2[1], t[0] - s2[0])
    r1 = float(np.hypot(*(t - s1)))
    r2 = float(np.hypot(*(t - s2)))
    A = np.array([[-math.sin(a1), math.cos(a1)], [-math.sin(a2), math.cos(a2)]])
    det = float(np.linalg.det(A))          # = sin(a1-a2)
    sin_g = abs(det)
    degenerate = sin_g < 1e-9
    gamma = float(math.degrees(math.asin(min(1.0, sin_g))))
    baseline = float(np.hypot(*(s2 - s1)))
    if degenerate:
        return dict(r1=r1, r2=r2, gamma_deg=gamma, baseline=baseline, sin_gamma=sin_g,
                    drms=float("inf"), cep90=float("inf"), cov=[[float("inf")] * 2] * 2,
                    eig=[float("inf"), float("inf")], drms_closed=float("inf"), degenerate=True)
    Ainv = np.linalg.inv(A)
    cov = sig**2 * (r1**2 * np.outer(Ainv[:, 0], Ainv[:, 0]) +
                    r2**2 * np.outer(Ainv[:, 1], Ainv[:, 1]))
    ev = np.linalg.eigvalsh(cov)
    drms = float(np.sqrt(np.trace(cov)))
    return dict(r1=r1, r2=r2, gamma_deg=gamma, baseline=baseline, sin_gamma=sin_g,
                drms=drms, cep90=float(1.1774 * math.sqrt(max(ev))),
                cov=cov.tolist(), eig=[float(x) for x in ev],
                drms_closed=float(sig * math.hypot(r1, r2) / sin_g), degenerate=False)
