# -*- coding: utf-8 -*-
"""全部图件：Agg 后端，SimHei，pdf + png 成对落 figures/。"""
from __future__ import annotations

import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Patch, Rectangle

import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)

for cand in ("SimHei", "Microsoft YaHei"):
    try:
        font_manager.findfont(cand, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [cand]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"font.size": 7.6, "axes.titlesize": 8.0, "axes.labelsize": 7.8,
                     "xtick.labelsize": 7.0, "ytick.labelsize": 7.0, "legend.fontsize": 6.8,
                     "axes.linewidth": 0.6, "lines.linewidth": 0.9})

CLR = {"T1": "#c0392b", "T2": "#1f4e79", "T3": "#2e7d32", "T4": "#6a1b9a"}


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))


def save(fig, stem):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG, stem + "." + ext), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("[fig]", stem)


def site(ax, which="both"):
    for (nm, x1, x2, y1, y2, h) in C.BUILDINGS:
        ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, facecolor="#9e9e9e",
                               edgecolor="#4d4d4d", lw=0.5, alpha=0.75, zorder=2))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2, "%s\nh=%g" % (nm, h), ha="center", va="center",
                fontsize=6.4, color="white", zorder=3)
    if which in ("both", "veh"):
        for v, (x, y) in C.VEH0.items():
            ax.plot(x, y, "^", ms=4.2, mfc="#1565c0", mec="white", mew=0.4, zorder=5)
            ax.annotate(v, (x, y), textcoords="offset points", xytext=(3.5, -2.5), fontsize=6.2,
                        color="#0d47a1", zorder=6)
    if which in ("both", "tgt"):
        off = {"T1": (4, 3), "T2": (-40, 5), "T3": (4, 3)}
        for t in C.TARGETS:
            if t == "T4":
                continue
            x, y, _ = C.target_xyz(t)
            ax.plot(x, y, "*", ms=7.0, mfc=CLR[t], mec="black", mew=0.35, zorder=7)
            lab = t + ("（悬于 B3 上 H=35）" if t == "T2" else "")
            ax.annotate(lab, (x, y), textcoords="offset points", xytext=off.get(t, (4, 3)),
                        fontsize=6.4, color=CLR[t], weight="bold", zorder=8,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.72) if t == "T2" else None)
    ax.set_xlim(-1, 101)
    ax.set_ylim(-1, 101)
    ax.set_aspect("equal")
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(length=2, pad=1.5)


def fig1(p1):
    fig, axs = plt.subplots(2, 3, figsize=(7.0, 4.9))
    for j, t in enumerate(("T1", "T2", "T3")):
        for i, mode in enumerate(("3d", "planar")):
            ax = axs[i, j]
            obs = C.observability(t, 1.0, mode)
            X, Y, O = obs["X"], obs["Y"], obs["obs"] & obs["geom"]
            ax.pcolormesh(np.arange(-0.5, 100.5), np.arange(-0.5, 100.5),
                          (O & obs["elev"]).T if i == 0 else (O & obs["elev"]).T,
                          cmap="YlGnBu", vmin=0, vmax=1.35, shading="flat", zorder=1)
            site(ax)
            d = p1["observability"][t]
            frac = d["frac_of_field_3d"] if i == 0 else d["frac_of_field_planar"]
            ax.set_title("%s  %s  %.2f%%（1 m 栅格）" % (t, "三维视线" if i == 0 else "平面阴影", 100 * frac))
    axs[0, 0].set_ylabel("三维判定")
    axs[1, 0].set_ylabel("平面阴影")
    h = [Patch(facecolor="#4a9fc4", label="可观测格"),
         Patch(facecolor="#9e9e9e", label="楼体"),
         plt.Line2D([], [], marker="^", ls="", color="#1565c0", label="车辆"),
         plt.Line2D([], [], marker="*", ls="", color="#c0392b", label="目标")]
    fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "fig1_observability")


def fig2(p1):
    t = "T1"
    obs = C.observability(t, 0.5, "3d")
    ok = obs["obs"] & obs["geom"] & obs["elev"]
    X, Y = obs["X"][ok], obs["Y"][ok]
    tx, ty, _ = C.target_xyz(t)
    r = np.hypot(X - tx, Y - ty)
    q = 1.0 / r
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    sc = ax.scatter(X, Y, c=q, s=1.2, cmap="viridis", vmin=0, vmax=float(q.max()), zorder=2)
    site(ax)
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("Q = 1/r  (1/m)")
    cb.ax.tick_params(labelsize=6.4)
    d = p1["p1_T1"]["tie"]["chosen"]
    ax.plot(d["x"], d["y"], marker="o", ms=6.0, mfc="none", mec="red", mew=1.1, zorder=8)
    ax.annotate("sup Q=%.4f\n(x,y)=(%.2f,%.2f)\n%s  %.2f s" % (d["q"], d["x"], d["y"], d["vehicle"], d["travel_s"]),
                (d["x"], d["y"]), textcoords="offset points", xytext=(-62, 12), fontsize=6.4,
                color="red", zorder=9,
                bbox=dict(fc="white", ec="red", lw=0.4, alpha=0.85, pad=2.2))
    ax.set_xlabel("x / m")
    ax.set_ylabel("y / m")
    ax.set_title("T1 可观测域内的 Q=1/r 场与最优站址")
    fig.tight_layout()
    save(fig, "fig2_q_field")


def fig3(p2):
    a = p2["p2_1"]["attained"]
    obs = C.observability("T2", 2.0, "3d")
    ok = obs["obs"] & obs["geom"] & obs["elev"]
    X, Y = obs["X"][ok], obs["Y"][ok]
    tx, ty, _ = C.target_xyz("T2")
    best = np.full(X.shape, np.nan)
    for i in range(len(X)):
        if i % 3:
            continue
        for j in range(i + 1, len(X)):
            sg = abs((tx - X[i]) * (ty - Y[j]) - (ty - Y[i]) * (tx - X[j])) / (
                np.hypot(tx - X[i], ty - Y[i]) * np.hypot(tx - X[j], ty - Y[j]))
            if sg < 0.35:
                continue
            v = C.SIGMA_RAD * math.sqrt((tx - X[i]) ** 2 + (ty - Y[i]) ** 2
                                        + (tx - X[j]) ** 2 + (ty - Y[j]) ** 2) / sg
            best[i] = v if np.isnan(best[i]) else min(best[i], v)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw=dict(width_ratios=[1.35, 1]))
    m = ~np.isnan(best)
    sc = ax.scatter(X[m], Y[m], c=np.log10(best[m]), s=6, cmap="viridis_r", vmin=-1.1, vmax=0.4)
    site(ax, "veh")
    ax.plot(tx, ty, "*", ms=7.0, mfc=CLR["T2"], mec="black", mew=0.35, zorder=7)
    ax.annotate("T2", (tx, ty), textcoords="offset points", xytext=(-16, 6), fontsize=6.6,
                color=CLR["T2"], weight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.72))
    for st, nm in ((a["s1"], "s1"), (a["s2"], "s2")):
        ax.plot(st[0], st[1], "o", ms=5.2, mfc="none", mec="cyan", mew=1.0, zorder=8)
        ax.annotate(nm, st, textcoords="offset points", xytext=(4, -8), fontsize=6.4, color="#00838f",
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.75))
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("log10(该站可达最小 DRMS/m)，越黄越小")
    cb.ax.tick_params(labelsize=6.4)
    ax.set_title("T2：单站最优伙伴 DRMS（2 m 站址）")
    g = np.array([x["gamma_deg"] for x in p2["p2_1"]["gamma_sweep"]])
    dr = np.array([x["drms"] for x in p2["p2_1"]["gamma_sweep"]])
    ax2.semilogy(g, dr, "o-", ms=2.6, lw=0.9, color="#1f4e79")
    gg = np.linspace(0.5, 179.5, 400)
    ax2.semilogy(gg, C.SIGMA_RAD * math.sqrt(2) * p2["p2_1"]["r_min_analytic"] / np.sin(np.radians(gg)),
                 lw=0.7, color="grey", ls="--")
    ax2.axhline(p2["p2_1"]["drms_lower_bound"], color="#c0392b", lw=0.7, ls=":")
    ax2.annotate("下界 %.4f m" % p2["p2_1"]["drms_lower_bound"], (95, p2["p2_1"]["drms_lower_bound"]),
                 textcoords="offset points", xytext=(-70, 4), fontsize=6.4, color="#c0392b")
    ax2.axvline(90, color="#2e7d32", lw=0.6, ls="-.")
    ax2.set_xlabel("两方位线夹角 γ / (°)")
    ax2.set_ylabel("DRMS / m")
    ax2.set_title("DRMS(γ) 的退化")
    ax2.set_ylim(0.1, 20)
    fig.tight_layout()
    save(fig, "fig3_drms")


def fig4(p2):
    plans = [("无距离上限（makespan %.2f s）" % p2["p2_2"]["unconstrained"]["makespan"],
              p2["p2_2"]["unconstrained"]),
             ("R_cap=20 m（makespan %.2f s）" % p2["p2_2"]["cap20"]["makespan"], p2["p2_2"]["cap20"])]
    fig, axs = plt.subplots(2, 1, figsize=(7.0, 4.2), sharex=True)
    for ax, (title, pl) in zip(axs, plans):
        for k, v in enumerate(C.VEH0):
            for e in pl["timeline"].get(v, []):
                c = CLR[e["alert"]]
                ax.barh(k, e["arrive"] - e["depart"], left=e["depart"], height=0.52,
                        color=c, alpha=0.22, edgecolor="none")
                ax.barh(k, e["ready"] - e["arrive"], left=e["arrive"], height=0.52,
                        color=c, alpha=0.42, edgecolor="none")
                ax.barh(k, e["obs_end"] - e["obs_start"], left=e["obs_start"], height=0.52,
                        color=c, alpha=0.95, edgecolor="black", lw=0.3)
                ax.barh(k, e["free"] - e["obs_end"], left=e["obs_end"], height=0.52,
                        color=c, alpha=0.42, edgecolor="none")
                ax.text(e["obs_start"] + 0.25, k, e["alert"], va="center", ha="left",
                        fontsize=6.0, color="white", zorder=6)
        ax.axvline(pl["makespan"], color="black", lw=0.8, ls="--")
        ax.annotate("makespan %.2f" % pl["makespan"], (pl["makespan"], 4.45), fontsize=6.4,
                    ha="right", va="top")
        ax.set_yticks(range(5))
        ax.set_yticklabels(list(C.VEH0))
        ax.set_ylim(-0.6, 4.6)
        ax.set_title(title, loc="left")
        ax.grid(axis="x", lw=0.3, alpha=0.5)
    axs[-1].set_xlabel("t / s")
    h = [Patch(facecolor="#777777", alpha=0.25, label="行驶"),
         Patch(facecolor="#777777", alpha=0.45, label="调转/复位"),
         Patch(facecolor="#777777", alpha=0.95, label="联合观测 5 s")]
    h += [Patch(facecolor=CLR[t], label=t) for t in ("T1", "T2", "T3")]
    fig.legend(handles=h, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, -0.025))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, "fig4_gantt")


def fig5(p3):
    p = p3["p3"]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.6), gridspec_kw=dict(width_ratios=[1.2, 1, 1]))
    s = np.linspace(0, 120, 600)
    loc = (0.3 + 0.02 * s) / 40.0 * 180 / math.pi
    tot = np.sqrt(loc ** 2 + 0.8 ** 2 + 0.6 ** 2)
    ax = axs[0]
    ax.plot(s, tot, color="#1f4e79", label="合成 sigma")
    ax.plot(s, loc, color="#c0392b", ls="--", lw=0.7, label="定位项")
    ax.plot(s, np.sqrt(0.8 ** 2 + 0.6 ** 2) * np.ones_like(s), color="grey", ls=":", lw=0.7, label="云台合成")
    ax.axhline(p["budget_deg"], color="black", lw=0.7, ls="-.", label="预算 5°/z")
    ax.axvline(p["s_max"], color="#2e7d32", lw=0.7, ls="-.")
    ax.annotate("s_max=%.2f m" % p["s_max"], (p["s_max"], p["budget_deg"]),
                textcoords="offset points", xytext=(6, -20), fontsize=6.4, color="#2e7d32",
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8))
    ax.set_xlabel("行程 s / m")
    ax.set_ylabel("sigma / (deg)")
    ax.set_ylim(0, 5.2)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("合成误差与预算")
    ax = axs[1]
    aa, bb = p["ab_constraint"]["vertices"][1][0], p["ab_constraint"]["vertices"][0][1]
    ax.fill([0, aa, 0], [0, 0, bb], color="#2e7d32", alpha=0.22, edgecolor="#2e7d32", lw=0.8)
    ax.plot([0, aa], [bb, 0], color="#2e7d32", lw=1.0)
    ax.plot(0.3, 0.02, "o", ms=4, color="#c0392b")
    ax.annotate("题面 a=0.3,b=0.02\n(越界)", (0.3, 0.02), textcoords="offset points", xytext=(4, 4),
                fontsize=6.2, color="#c0392b")
    ax.annotate("b_max=%.5f" % bb, (0, bb), textcoords="offset points", xytext=(3, -9), fontsize=6.2)
    ax.set_xlabel("零偏 a / m")
    ax.set_ylabel("系数 b（无量纲，m 每 m）")
    ax.set_xlim(-0.02, 1.75)
    ax.set_ylim(-0.0008, 0.023)
    ax.set_title("s=80 m 可行域 a+80b≤%.3f m（≈%.3f°）" % (p["sigma_s_allow_m"], p["sigma_loc_allow_deg"]))
    ax = axs[2]
    if "linearization_check" in p:
        lc = p["linearization_check"]
        ss = [x["s"] for x in lc]
        mcp = [x["mc_exact"] for x in lc]
        cf = [x["closed"] for x in lc]
        ax.plot(ss, mcp, "o-", ms=2.6, lw=0.8, color="#c0392b", label="蒙特卡洛 1e5")
        ax.plot(ss, cf, "--", lw=0.8, color="#1f4e79", label="线性化闭式")
        ax.legend(frameon=False)
    ax.axhline(0.95, color="black", lw=0.6, ls=":")
    ax.set_xlabel("行程 s / m")
    ax.set_ylabel("P(|Δψ|≤5 deg)")
    ax.set_title("线性化与仿真互验")
    fig.tight_layout()
    save(fig, "fig5_p3")


def fig6(p4):
    d = p4["p4"]
    rows = d["rows"]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.5))
    ax = axs[0]
    v = sorted({round(x["keep_strict"]["eta"], 3) for x in rows}
               | {round(x["keep"]["eta"], 3) for x in rows}
               | {round(x["resched"]["eta"], 3) for x in rows})
    k0 = [sum(1 for x in rows if abs(x["keep_strict"]["eta"] - u) < 1e-9) / len(rows) for u in v]
    k1 = [sum(1 for x in rows if abs(x["keep"]["eta"] - u) < 1e-9) / len(rows) for u in v]
    k2 = [sum(1 for x in rows if abs(x["resched"]["eta"] - u) < 1e-9) / len(rows) for u in v]
    w = 0.26
    ax.bar(np.arange(len(v)) - w, k0, w, color="#e08e0b", label="保持原计划")
    ax.bar(np.arange(len(v)), k1, w, color="#c0392b", label="保持+补派T4")
    ax.bar(np.arange(len(v)) + w, k2, w, color="#1f4e79", label="重调度")
    ax.set_xticks(range(len(v)))
    ax.set_xticklabels(["%g" % u for u in v])
    ax.set_xlabel("完成率 η")
    ax.set_ylabel("频率")
    ax.legend(frameon=False)
    ax.set_title("η 分布（%d 次抽样）" % len(rows))
    ax = axs[1]
    tr = np.array([x["t_rec"] for x in rows])
    for pol, cl, nm in (("keep", "#c0392b", "保持+补派"), ("resched", "#1f4e79", "重调度")):
        yy = np.array([max(x["starts_" + pol].values()) for x in rows])
        ok = np.array([x[pol]["k"] == x[pol]["N"] for x in rows])
        ax.plot(tr[ok], yy[ok], ".", ms=1.4, color=cl, alpha=0.55)
        ax.plot(tr[~ok], yy[~ok], ".", ms=1.4, mfc="none", mec=cl, alpha=0.8)
    ax.set_xlabel("通信恢复时刻 t_rec / s")
    ax.set_ylabel("已服务警报最晚开始 / s")
    ax.set_title("已服务最晚开始（空心=有警报未完成）")
    ax = axs[2]
    H = [x["horizon"] for x in d["by_horizon"]]
    ax.plot(H, [x["keep_eta"] for x in d["by_horizon"]], "o-", ms=3, color="#c0392b", label="保持")
    ax.plot(H, [x["resched_eta"] for x in d["by_horizon"]], "s-", ms=3, color="#1f4e79", label="重调度")
    ax.set_xlabel("任务窗口上限 / s")
    ax.set_ylabel("平均 η")
    ax.set_title("窗口长度决定策略优劣")
    ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "fig6_p4")


def main():
    p1 = load("p1.json")
    p2 = load("p2.json")
    p3 = load("p3.json")
    p4 = load("p4.json")
    fig1(p1)
    fig2(p1)
    fig3(p2)
    fig4(p2)
    fig5(p3)
    fig6(p4)


if __name__ == "__main__":
    main()