# -*- coding: utf-8 -*-
"""公共常数、坐标系、开普勒解与曲线代数次数检验。

一切长度以 AU 为单位、时间以天为单位（除非函数名另注）。
角度内部一律弧度，只在输出 JSON 时转成度/角秒。
"""
from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"
DATA.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# ---------------------------------------------------------------- 常数
AU = 1.495978707e11          # m, IAU 2012 定义值
C_LIGHT = 299792458.0        # m/s
DAY = 86400.0
YEAR = 365.25 * DAY
CENTURY = 100.0 * YEAR
ARCSEC = np.pi / 180.0 / 3600.0
MAS = ARCSEC / 1000.0

GM_SUN_SI = 1.32712440018e20               # m^3 s^-2, IAU 2015
GM_SUN = GM_SUN_SI * DAY**2 / AU**3        # AU^3 day^-2

# 行星轨道根数（J2000，NASA planetary fact sheet / IAU）
PLANETS = {
    "Venus": dict(a=0.723332, e=0.006772, i_deg=3.39458, Om_deg=76.680, om_deg=54.884),
    "Earth": dict(a=1.000000, e=0.016709, i_deg=0.00005, Om_deg=174.9, om_deg=288.1),
    "Mars":  dict(a=1.523679, e=0.093400, i_deg=1.85061, Om_deg=49.558, om_deg=286.502),
    "Mercury": dict(a=0.387098, e=0.205630, i_deg=7.00487, Om_deg=48.331, om_deg=29.124),
}

# 水星近日点额外进动（扣掉行星摄动后的观测残差），Clemence 1947 / GR 预言
MERCURY_PREC_ARCSEC_PER_CY = 42.98


# ---------------------------------------------------------------- 旋转
def rot_z(t):
    c, s = np.cos(t), np.sin(t)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rot_x(t):
    c, s = np.cos(t), np.sin(t)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def orbit_matrix(i, Om, om):
    """轨道平面 -> 黄道系：Rz(Om) Rx(i) Rz(om)。"""
    return rot_z(Om) @ rot_x(i) @ rot_z(om)


def sky_projection(theta):
    """返回 (e_hat, e1, e2)：视线方向与天球面两轴。地球在 (cosθ, sinθ)·dE。"""
    e_hat = np.array([np.cos(theta), np.sin(theta), 0.0])   # 恒星->地球方向
    e1 = np.array([-np.sin(theta), np.cos(theta), 0.0])     # 黄道面内、垂直视线
    e2 = np.array([0.0, 0.0, 1.0])                          # 黄道北极
    return e_hat, e1, e2


# ---------------------------------------------------------------- 开普勒
def kepler_E(M, e, tol=1e-14, itmax=80):
    """向量化 Newton 解开普勒方程 E - e sinE = M。"""
    M = np.asarray(M, dtype=float)
    E = M + e * np.sin(M) / (1.0 - e * np.cos(M) + 1e-300)
    for _ in range(itmax):
        f = E - e * np.sin(E) - M
        fp = 1.0 - e * np.cos(E)
        dE = -f / fp
        E = E + dE
        if np.max(np.abs(dE)) < tol:
            break
    return E


def orbit_points(a, e, i, Om, om, M):
    """真轨道三维位置 (3,N)，单位 AU。M 为平近点角（弧度）。"""
    E = kepler_E(M, e)
    xi = a * (np.cos(E) - e)
    eta = a * np.sqrt(1.0 - e * e) * np.sin(E)
    R = orbit_matrix(i, Om, om)
    return R @ np.stack([xi, eta, np.zeros_like(xi)])


def orbit_frame(a, e, i, Om, om):
    """返回 (p_hat, q_hat, center)：r = center + a cosE p + b sinE q。"""
    R = orbit_matrix(i, Om, om)
    p_hat = R @ np.array([np.cos(om), np.sin(om), 0.0])
    q_hat = R @ np.array([-np.sin(om), np.cos(om), 0.0])
    center = -a * e * p_hat
    return p_hat, q_hat, center, a * np.sqrt(1.0 - e * e)


# ---------------------------------------------------------------- 视位置
def apparent_sky(r, theta, dE):
    """精确视位置：天球切平面（gnomonic，标准坐标 ξ=tan）投影。

    观者在 R_E = dE·e_hat，恒星在原点。视线到恒星的射线与过恒星、
    垂直视线的切平面相交，交点坐标即 s。推导：把 r 沿观者->r 的射线
    投到平面 {x·e_hat = 0} 上，得 s = dE·r_perp/(dE - r·e_hat)。
    这是一次中心投影（射影变换），故精确视曲线必为圆锥曲线。
    """
    e_hat, e1, e2 = sky_projection(theta)
    mu = e_hat @ r
    den = dE - mu
    s1 = dE * (e1 @ r) / den
    s2 = dE * (e2 @ r) / den
    rr = np.einsum("ij,ij->j", r, r)
    rho = np.sqrt(dE * dE - 2.0 * dE * mu + rr)
    return np.stack([s1, s2]), mu / dE, rr ** 0.5 / dE


def apparent_sin_chart(r, theta, dE):
    """另一套天球图卡：s = dE·sin(角距) 的横向分量（方向余弦图）。

    与 gnomonic 图只差二阶；用于估计"图卡选择"自身的系统差量级。
    """
    e_hat, e1, e2 = sky_projection(theta)
    mu = e_hat @ r
    rr = np.einsum("ij,ij->j", r, r)
    rho = np.sqrt(dE * dE - 2.0 * dE * mu + rr)
    return np.stack([dE * (e1 @ r) / rho, dE * (e2 @ r) / rho])


def apparent_orthographic(r, theta):
    """正交投影（dE -> ∞）：直接丢掉沿视线的分量。"""
    _, e1, e2 = sky_projection(theta)
    return np.stack([e1 @ r, e2 @ r])


def apparent_first_order(r, theta, dE):
    """一阶视差修正：s ≈ r_perp (1 + (r·e_hat)/dE)。"""
    e_hat, _, _ = sky_projection(theta)
    return apparent_orthographic(r, theta) * (1.0 + (e_hat @ r) / dE)


# ---------------------------------------------------------------- 代数次数
def _monomials(x, y, deg):
    powers, cols = [], []
    for d in range(deg + 1):
        for k in range(d + 1):
            powers.append((d - k, k))
            cols.append(x ** (d - k) * y ** k)
    return powers, np.stack(cols, axis=1)


def poly_curve_residual(X, deg):
    """把点集 X=(2,N) 拟合为 deg 次代数曲线，返回几何残差 RMS（AU）。

    系数向量按 mean|∇P| = 1 归一，残差 |P|/|∇P| 于是可直接跨次数比较。
    """
    x, y = X
    scale = max(np.max(np.abs(x)), np.max(np.abs(y)), 1e-12)
    xs, ys = x / scale, y / scale
    powers, A = _monomials(xs, ys, deg)
    colnorm = np.linalg.norm(A, axis=0)
    colnorm[colnorm == 0] = 1.0
    _, _, Vt = np.linalg.svd(A / colnorm, full_matrices=False)
    coef = Vt[-1] / colnorm
    P = A @ coef
    gx = np.zeros_like(xs)
    gy = np.zeros_like(ys)
    for c, (dx, dy) in zip(coef, powers):
        if dx:
            gx += c * dx * xs ** (dx - 1) * ys ** dy
        if dy:
            gy += c * xs ** dx * dy * ys ** (dy - 1)
    g = np.hypot(gx, gy)
    gmean = np.mean(g)
    if gmean <= 0:
        return np.inf
    # |P|/|∇P| 在归一化坐标里算，再乘回 AU
    res = np.abs(P) / g * scale
    return float(np.sqrt(np.mean(res**2)))


def conic_params(X):
    """拟合圆锥曲线并返回 (中心, 半轴 A>=B, 长轴方位角 rad, 残差)。"""
    x, y = X
    # 二次型 Q=[A,B/2;B/2,C]，线性项 d，常数 f
    D = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], axis=1)
    _, _, Vt = np.linalg.svd(D, full_matrices=False)
    A, B, C, Dd, E, F = Vt[-1]
    M = np.array([[A, B / 2.0], [B / 2.0, C]])
    lin = np.array([Dd, E])
    try:
        ctr = -0.5 * np.linalg.solve(M, lin)
    except np.linalg.LinAlgError:
        return None
    Fc = F + 0.5 * lin @ ctr
    w, V = np.linalg.eigh(M)
    k = -Fc
    axes = np.sqrt(np.abs(k / w)) if np.all(np.abs(w) > 0) else np.array([np.nan, np.nan])
    order = np.argsort(axes)[::-1]
    axes = axes[order]
    vec = V[:, order[0]]
    ang = float(np.arctan2(vec[1], vec[0]))
    return dict(center=ctr, A=float(axes[0]), B=float(axes[1]), angle=ang)


# ---------------------------------------------------------------- IO
def meta(title: str, extra: dict | None = None) -> dict:
    m = {
        "title": title,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "platform": platform.platform(),
        "units": "AU, day, rad; angles converted to deg/arcsec at output",
        "code_root": "code/",
    }
    if extra:
        m.update(extra)
    return m


def dump(name: str, payload: dict) -> Path:
    path = DATA / name
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=False)
    return path


def f(x, nd=6):
    """JSON 友好浮点：nd 位有效数字（不是小数位），小量不丢精度。"""
    v = float(x)
    if v == 0.0 or not np.isfinite(v):
        return 0.0 if v == 0.0 else None
    return float(f"{v:.{nd}g}")


# ---------------------------------------------------------------- 画图
def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt

    for cand in (r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"):
        if os.path.exists(cand):
            font_manager.fontManager.addfont(cand)
    plt.rcParams.update({
        "font.family": "SimHei",
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9.5,
        "legend.fontsize": 7.5,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.3,
    })
    return plt


def ascii_log(ax, which="both"):
    """对数轴刻度改成 ASCII '1e-3'，避开 SimHei 缺 U+2212 的问题。"""
    from matplotlib.ticker import FuncFormatter, NullFormatter

    def _f(v, _pos):
        if v <= 0:
            return ""
        e = int(round(np.log10(v)))
        m = v / 10.0 ** e
        return f"1e{e}" if abs(m - 1.0) < 1e-8 else f"{m:g}e{e}"

    fmt = FuncFormatter(_f)
    if "x" in which:
        ax.xaxis.set_major_formatter(fmt)
        ax.xaxis.set_minor_formatter(NullFormatter())
    if "y" in which:
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.set_minor_formatter(NullFormatter())
    return ax


_FONT_CACHE = {}


def _glyph_font():
    if "f" not in _FONT_CACHE:
        from matplotlib.ft2font import FT2Font
        path = r"C:\Windows\Fonts\simhei.ttf"
        _FONT_CACHE["f"] = FT2Font(path)
    return _FONT_CACHE["f"]


def missing_glyphs(fig):
    """遍历图里所有 Text，返回 SimHei 缺字形的 (文本, 字符) 列表。mathtext 段跳过。"""
    from matplotlib.text import Text
    font = _glyph_font()
    bad = []
    for t in fig.findobj(Text):
        s = t.get_text()
        if not s or "$" in s:
            continue
        for ch in s:
            if ord(ch) > 32 and font.get_char_index(ord(ch)) == 0:
                bad.append((s, ch, hex(ord(ch))))
    return bad


def savefig(fig, stem: str):
    bad = missing_glyphs(fig)
    if bad:
        raise RuntimeError(f"{stem}: SimHei 缺字形 {bad}")
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{stem}.{ext}", bbox_inches="tight", pad_inches=0.02)
    return stem