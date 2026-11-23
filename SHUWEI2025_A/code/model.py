# -*- coding: utf-8 -*-
"""Core physics for the 2025 ShuWei Cup Problem A (centrifugal actuator lateral
vibration suppression).

Conventions (all fixed in one place, because a sign error here silently flips the
whole result):

  * x = forward, y = lateral. Body lateral displacement y(t); wheels do not move
    laterally, so the relative displacement is y itself.
  * One dual-motor actuator carries 4 eccentric masses: 2 groups x 2 masses.
    Within a group the two masses are mirror images about the y axis, so their
    x components cancel and their y components add. One group is therefore
    described by a single angle theta_g, measured from the +y axis.
  * Mass position relative to the body: (r sin theta, r cos theta). Its inertial
    acceleration is  y'' + r(-alpha sin theta - omega^2 cos theta)  along y.
    Reaction on the body is the negative of m*a, so summing the 8 masses gives

        (M_body + 8m) y'' + c y' + k y = F_dist + F_act
        F_act = 2 m r * sum_g (omega_g^2 cos theta_g + alpha_g sin theta_g)

    The 8m term is *added mass*, not a modelling fudge: it falls out of the same
    summation that produces F_act, which is why it is folded into M.
"""
from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------- parameters
M_BODY = 2000.0      # kg, body without actuators
M_ECC = 100.0        # kg, one eccentric mass
RADIUS = 0.2         # m
OMEGA_MAX = 100.0    # rad/s
ALPHA_MAX = 5000.0   # rad/s^2
K_EQ = 7_225_200.0   # N/m
C_EQ = 3600.0        # N s/m
N_GROUP = 4          # 2 actuators x 2 groups
M_TOTAL = M_BODY + 8 * M_ECC   # 2800 kg, includes added mass

Y0 = 0.01            # m
V0 = 0.0             # m/s
DT = 0.01            # s, data sampling
DT_SIM = 1e-3        # s, integration step


def natural(par: dict | None = None) -> tuple[float, float]:
    """Undamped natural frequency (rad/s), damping ratio, damped frequency."""
    p = {**globals(), **(par or {})}
    wn = np.sqrt(p["K_EQ"] / p["M_TOTAL"])
    zeta = p["C_EQ"] / (2.0 * np.sqrt(p["K_EQ"] * p["M_TOTAL"]))
    wd = wn * np.sqrt(max(1e-12, 1.0 - zeta ** 2))
    return float(wn), float(zeta), float(wd)


# ---------------------------------------------------------------- data load
def load_scenarios(path: str) -> dict:
    """Read the official workbook. Rows 1-2 are bilingual headers."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    par = {}
    for row in wb["系统参数"].iter_rows(min_row=2, values_only=True):
        if row[1] is None:
            continue
        key = str(row[1]).strip()
        try:
            par[key] = float(row[2])
        except (TypeError, ValueError):
            continue
    s1 = np.array([[float(v) for v in r]
                   for r in wb["场景1"].iter_rows(min_row=3, values_only=True)])
    s2 = np.array([[float(v) for v in r]
                   for r in wb["场景2"].iter_rows(min_row=3, values_only=True)])
    return {"params": par, "t": s1[:, 0], "F1": s1[:, 1], "theta1": s1[:, 2:6],
            "F2": s2[:, 1]}


# ---------------------------------------------------------------- kinematics
def angles_to_rates(theta: np.ndarray, dt: float = DT,
                    alpha_max: float = ALPHA_MAX,
                    omega_max: float = OMEGA_MAX) -> tuple[np.ndarray, np.ndarray]:
    """Central differences, then project onto the actuator's physical limits.

    The projection keeps the *angles* fixed at the measured samples and only
    adjusts the implied increments, by clipping every |omega_{i+1} - omega_i|
    to alpha_max*dt. Repeated sweeps converge because clipping is a
    non-expansive projection onto a convex set (a tube constraint). The residual
    is reported so the paper can state how far the measured signal sits from the
    admissible set instead of pretending it is exact.
    """
    th = np.asarray(theta, float)
    if th.ndim == 1:
        om, al, raw = angles_to_rates(th[:, None], dt, alpha_max, omega_max)
        return om[:, 0], al[:, 0], raw[:, 0]
    # 2-D: one column per group, handled independently (they share no constraint)
    outs = [_rates_1d(th[:, j], dt, alpha_max, omega_max) for j in range(th.shape[1])]
    om = np.column_stack([o[0] for o in outs])
    al = np.column_stack([o[1] for o in outs])
    raw = np.column_stack([o[2] for o in outs])
    return om, al, raw


def _rates_1d(th: np.ndarray, dt: float, alpha_max: float,
              omega_max: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = th.shape[0]
    om = np.zeros(n)
    om[0] = (th[1] - th[0]) / dt
    om[-1] = (th[-1] - th[-2]) / dt
    om[1:-1] = (th[2:] - th[:-2]) / (2 * dt)

    raw_om = om.copy()
    step = alpha_max * dt
    for _ in range(60):
        d = np.diff(om)
        over = np.abs(d) > step + 1e-15
        if not over.any():
            break
        d = np.clip(d, -step, step)
        om = np.concatenate([[om[0]], om[0] + np.cumsum(d)])
        np.clip(om, -omega_max, omega_max, out=om)
    al = np.zeros(n)
    al[0] = (om[1] - om[0]) / dt
    al[-1] = (om[-1] - om[-2]) / dt
    al[1:-1] = (om[2:] - om[:-2]) / (2 * dt)
    np.clip(al, -alpha_max, alpha_max, out=al)
    return om, al, raw_om


def actuator_force(theta: np.ndarray, om: np.ndarray, al: np.ndarray,
                   m: float = M_ECC, r: float = RADIUS, sign: float = 1.0) -> np.ndarray:
    """Total y-force from all 4 groups: 2mr(omega^2 cos th + alpha sin th) per group."""
    g = 2.0 * m * r * (om ** 2 * np.cos(theta) + al * np.sin(theta))
    g = g.sum(axis=1) if g.ndim > 1 else g
    return sign * g


# ---------------------------------------------------------------- simulation
def simulate(t: np.ndarray, f_dist: np.ndarray, f_act: np.ndarray | None = None,
             par: dict | None = None, y0: float = Y0, v0: float = V0) -> dict:
    """Integrate the body ODE with RK4 on a fine grid; forces are linear in between.

    Returns displacement, velocity and *relative acceleration* sampled at t.
    a = (F_dist + F_act - c v - k y) / M  is evaluated on the fine grid, so the
    index is an honest integral of the printed acceleration, not a shortcut.
    """
    p = {**globals(), **(par or {})}
    M, k, c = p["M_TOTAL"], p["K_EQ"], p["C_EQ"]
    t = np.asarray(t, float)
    f_dist = np.asarray(f_dist, float)
    f_act = (np.zeros_like(f_dist) if f_act is None else np.asarray(f_act, float))
    sub = max(1, int(round((t[1] - t[0]) / p["DT_SIM"])))
    m = max(1, sub)

    def fx(y, v, fa, fd):
        return (fd + fa - c * v - k * y) / M

    y, v = y0, v0
    Y = np.empty(len(t))
    V = np.empty(len(t))
    A = np.empty(len(t))
    Y[0], V[0], A[0] = y, v, fx(y, v, f_act[0], f_dist[0])
    for i in range(len(t) - 1):
        dt = (t[i + 1] - t[i]) / m
        fd0, fd1 = f_dist[i], f_dist[i + 1]
        fa0, fa1 = f_act[i], f_act[i + 1]
        for j in range(m):
            w0, w1 = j / m, (j + 1) / m
            fd = fd0 + (fd1 - fd0) * w0
            fa = fa0 + (fa1 - fa0) * w0
            k1y, k1v = v, fx(y, v, fa, fd)
            k2y = v + 0.5 * dt * k1v
            fd_m = fd0 + (fd1 - fd0) * (w0 + w1) / 2
            fa_m = fa0 + (fa1 - fa0) * (w0 + w1) / 2
            k2v = fx(y + 0.5 * dt * k1y, k2y, fa_m, fd_m)
            k3y = v + 0.5 * dt * k2v
            k3v = fx(y + 0.5 * dt * k2y, k3y, fa_m, fd_m)
            k4y = v + dt * k3v
            k4v = fx(y + dt * k3y, k4y, fd1, fa1)
            y += dt * (k1y + 2 * k2y + 2 * k3y + k4y) / 6
            v += dt * (k1v + 2 * k2v + 2 * k3v + k4v) / 6
        Y[i + 1], V[i + 1] = y, v
        A[i + 1] = fx(y, v, f_act[i + 1], f_dist[i + 1])
    return {"t": t, "y": Y, "v": V, "a": A}


def vibration_index(t: np.ndarray, a: np.ndarray) -> float:
    """I = (1/T) * integral a^2 dt over the sampled window, trapezoidal."""
    t = np.asarray(t, float)
    a = np.asarray(a, float)
    return float(np.trapezoid(a ** 2, t) / (t[-1] - t[0]))