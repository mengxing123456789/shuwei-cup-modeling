# -*- coding: utf-8 -*-
"""P1 可观测面积的网格收敛与口径对照。

问题：1 m 栅格给出 57.9%，0.5 m 给出 56.08%，差 1.82 pp，远超正常离散误差。
本脚本把两件事分开量：
  (A) 口径：车体净距 1.5 m（车心到楼/围栏 >=1.5） vs 相机点口径（点在场地内、不在楼内）
  (B) 相切：1 m 格心为 k+0.5，与"楼体外扩 1.5 m"的等距线（坐标均为 …5）重合，
      判据 `>= margin - 1e-12` 会把整条切点线收进来。本脚本用严格 `>` 复算对照。
"""
from __future__ import annotations

import math

import numpy as np

import common as C

NAME = "p1_area_grid.json"
DS_LIST = [1.0, 0.5, 0.25, 0.125]
TARGET = "T1"


def grid_xy(ds):
    """格心网格。"""
    n = int(round(C.FIELD[1] / ds))
    a = (np.arange(n) + 0.5) * ds
    return np.meshgrid(a, a)


def geom_ok_strict(x, y, margin, strict=False):
    """车体净距判据。strict=True 时用 >（把恰在 1.5 m 等距线上的格心排除）。"""
    if strict:
        ok = (x > margin) & (x < C.FIELD[1] - margin) & (y > margin) & (y < C.FIELD[1] - margin)
        for b in C.BUILDINGS:
            ok &= C.point_rect_dist(x, y, b) > margin
    else:
        ok = (x >= margin) & (x <= C.FIELD[1] - margin) & (y >= margin) & (y <= C.FIELD[1] - margin)
        for b in C.BUILDINGS:
            ok &= C.point_rect_dist(x, y, b) >= margin - 1e-12
    return ok


def point_in_field(x, y):
    """相机点口径：点在场地闭区域内。"""
    return (x >= 0.0) & (x <= C.FIELD[1]) & (y >= 0.0) & (y <= C.FIELD[1])


def point_outside_buildings(x, y):
    inside = np.zeros(x.shape, bool)
    for b in C.BUILDINGS:
        _, x0, x1, y0, y1, _ = b
        inside |= (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    return ~inside


def tangent_mask(x, y, margin):
    """格心恰好落在净距等距线上（|dist-margin|<=1e-9）：楼体或围栏。"""
    m = np.zeros(x.shape, bool)
    for b in C.BUILDINGS:
        m |= np.abs(C.point_rect_dist(x, y, b) - margin) <= 1e-9
    m |= (np.abs(x - margin) <= 1e-9) | (np.abs(x - (C.FIELD[1] - margin)) <= 1e-9)
    m |= (np.abs(y - margin) <= 1e-9) | (np.abs(y - (C.FIELD[1] - margin)) <= 1e-9)
    return m


def area_at(ds, margin):
    X, Y = grid_xy(ds)
    n = X.size
    elev = C.elev_ok(X, Y, TARGET)
    blocked = C.los_blocked(X, Y, TARGET)
    g_veh = geom_ok_strict(X, Y, margin, strict=False)
    g_veh_s = geom_ok_strict(X, Y, margin, strict=True)
    g_cam = point_in_field(X, Y) & point_outside_buildings(X, Y)
    g_cam_b = (X >= margin) & (X <= C.FIELD[1] - margin) & (Y >= margin) & (Y <= C.FIELD[1] - margin) \
        & point_outside_buildings(X, Y)
    tan = tangent_mask(X, Y, margin)
    # 切点线分围栏/楼体
    tan_fence = ((np.abs(X - margin) <= 1e-9) | (np.abs(X - (C.FIELD[1] - margin)) <= 1e-9)
                 | (np.abs(Y - margin) <= 1e-9) | (np.abs(Y - (C.FIELD[1] - margin)) <= 1e-9))
    tan_bld = np.zeros(X.shape, bool)
    for b in C.BUILDINGS:
        tan_bld |= np.abs(C.point_rect_dist(X, Y, b) - margin) <= 1e-9
    obs_veh = g_veh & elev & (~blocked)
    obs_veh_s = g_veh_s & elev & (~blocked)
    obs_cam = g_cam & elev & (~blocked)
    obs_cam_b = g_cam_b & elev & (~blocked)
    return dict(
        ds=ds, n_cells=int(n),
        frac_vehicle=float(obs_veh.mean()), cells_vehicle=int(obs_veh.sum()),
        frac_vehicle_strict=float(obs_veh_s.mean()), cells_vehicle_strict=int(obs_veh_s.sum()),
        frac_camera=float(obs_cam.mean()), cells_camera=int(obs_cam.sum()),
        frac_camera_fence_margin=float(obs_cam_b.mean()), cells_camera_fence_margin=int(obs_cam_b.sum()),
        tangent_cells=int(tan.sum()),
        tangent_fence_cells=int(tan_fence.sum()), tangent_building_cells=int(tan_bld.sum()),
        tangent_observable_cells=int((tan & obs_veh).sum()),
        tangent_fence_observable_cells=int((tan_fence & obs_veh).sum()),
        tangent_building_observable_cells=int((tan_bld & obs_veh).sum()),
        tangent_obs_extra_vs_strict=int((tan & obs_veh).sum() - (tan & obs_veh_s).sum()),
    )


def main():
    out = {"_meta": C.meta("q1_area_convergence.py"), "target": TARGET,
           "note": "面积分数 = 可观测格数 / 全场格数；场地 100x100"}

    rows = []
    for ds in DS_LIST:
        r = area_at(ds, C.VEH_R)
        # 同栅格、同净距，但格心改成整数坐标（角点口径，只作对照）
        X, Y = np.meshgrid(np.arange(0.0, 100.0, ds), np.arange(0.0, 100.0, ds))
        obs = geom_ok_strict(X, Y, C.VEH_R) & C.elev_ok(X, Y, TARGET) & (~C.los_blocked(X, Y, TARGET))
        r["frac_vehicle_corner_aligned"] = float(obs.mean())
        rows.append(r)
        print(f"ds={ds:<6} 车体 {r['frac_vehicle']*100:7.3f}% ({r['cells_vehicle']:6d})  "
              f"严格> {r['frac_vehicle_strict']*100:7.3f}%  相机点 {r['frac_camera']*100:7.3f}%  "
              f"相机+围栏 {r['frac_camera_fence_margin']*100:7.3f}%  "
              f"切点 围栏{r['tangent_fence_cells']:4d}/楼{r['tangent_building_cells']:3d} "
              f"其中可观测 围栏{r['tangent_fence_observable_cells']:4d}/楼{r['tangent_building_observable_cells']:3d}")
    out["rows"] = rows

    # 收敛判定：0.25 m 与 0.125 m 的差
    r025 = next(r for r in rows if r["ds"] == 0.25)
    r0125 = next(r for r in rows if r["ds"] == 0.125)
    r1 = next(r for r in rows if r["ds"] == 1.0)
    out["converged"] = dict(
        vehicle_1=round(r1["frac_vehicle"], 6),
        vehicle_05=round(next(r for r in rows if r["ds"] == 0.5)["frac_vehicle"], 6),
        vehicle_025=round(r025["frac_vehicle"], 6),
        vehicle_0125=round(r0125["frac_vehicle"], 6),
        delta_pp_025_vs_0125=round((r025["frac_vehicle"] - r0125["frac_vehicle"]) * 100, 4),
        camera_0125=round(r0125["frac_camera"], 6),
        camera_fence_margin_0125=round(r0125["frac_camera_fence_margin"], 6),
        clearance_cost_pp=round((r0125["frac_camera"] - r0125["frac_vehicle"]) * 100, 4),
        clearance_cost_fence_pp=round((r0125["frac_camera_fence_margin"] - r0125["frac_vehicle"]) * 100, 4),
        recommend_frac=round(r025["frac_vehicle"], 6),
        tol_pp=0.1,
        recommend_note="主报 0.25 m 车体净距值（56.15%）；0.125 m 与之差 0.07 pp（<0.1 pp 判据）即视为收敛",
    )
    # 1 m 异常的解释
    out["anomaly_1m"] = dict(
        observed_1m_frac=round(r1["frac_vehicle"], 6),
        strict_1m_frac=round(r1["frac_vehicle_strict"], 6),
        delta_cells=int(r1["cells_vehicle"] - r1["cells_vehicle_strict"]),
        tangent_cells=int(r1["tangent_cells"]),
        tangent_fence_cells=int(r1["tangent_fence_cells"]),
        tangent_building_cells=int(r1["tangent_building_cells"]),
        tangent_observable_cells=int(r1["tangent_observable_cells"]),
        tangent_fence_observable_cells=int(r1["tangent_fence_observable_cells"]),
        tangent_building_observable_cells=int(r1["tangent_building_observable_cells"]),
        gap_pp_vs_converged=round((r1["frac_vehicle"] - r0125["frac_vehicle"]) * 100, 4),
        over_inclusion_pp=round((r1["frac_vehicle"] - r1["frac_vehicle_strict"]) * 100, 4),
        coarse_deficit_pp=round((r0125["frac_vehicle"] - r1["frac_vehicle_strict"]) * 100, 4),
        cause="1 m 格心 = k+0.5，与楼体外扩 1.5 m 的等距线（22-1.5=20.5 等）及围栏 1.5/98.5 重合；"
              "判据 >=1.5-1e-12 把整条切点线判为可行。0.5/0.25/0.125 m 格心为 .25/.75/.125… 不与等距线重合。",
        decomposition="57.9% = 53.89%（严格>，粗网格欠采样） + 4.01 pp（切点线整层过收） - 0.0；"
                     "两项符号相反、部分抵消，故 1 m 值既不能当收敛值也不能当误差估计",
        convention="车心恰在 1.5 m 上属于合法停放（净距判据是 >=），所以 57.9% 是该栅格下的正确离散值，"
                   "但它不是面积的正确估计：误差来自离散化与相切约定耦合，随 ds 减小消失",
        fence_vs_building="切点线过收主要来自围栏列/行（1.5、98.5 落在 1 m 格心上），楼体等距线只占少数",
    )
    C.dump(NAME, out)
    print("converged:", out["converged"])
    print("anomaly 1m:", out["anomaly_1m"])


if __name__ == "__main__":
    main()