"""Figures 14 and 15 rebuilt from the single-definition risk table.

s04_q3 stored its top-ten list in insertion order and its ten-year probability
came from a fit that was not the one used for the return levels.  The paper now
reports p10 from the L-moment fit, so the two figures must be drawn from
q3_risk_table.csv, which is the artefact the table is built from.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import common as C

plt.rcParams.update({
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

OFFSETS = {
    "Zhengzhou": (6, -9), "Yuncheng": (-26, -9), "Hefei": (7, 4), "Nanjing": (7, -10),
    "Jinan": (6, 3), "Dalian": (7, -8), "Beijing": (6, 3), "Taiyuan": (6, 2),
    "Xining": (-24, 2), "Yinchuan": (-26, 4), "Hohhot": (6, 2), "Xi'an": (-24, -8),
    "Chengdu": (-26, 2), "Chongqing": (6, 2), "Fuzhou": (6, -8), "Haikou": (6, -8),
    "Guangzhou": (6, 2), "Nanning": (-24, 2), "Urumqi": (-24, 2), "Harbin": (6, 2),
    "Shenyang": (6, 2), "Kunming": (-22, -8), "Guiyang": (-24, 2), "Lanzhou": (-24, 2),
    "Wuhan": (6, 2), "Nanchang": (6, 2), "Hangzhou": (6, -8),
}


def main() -> None:
    t = pd.read_csv(C.RESULTS / "q3_risk_table.csv")
    coords = pd.read_csv(C.RESULTS / "q3_city_risk.csv")[["city", "lat", "lon"]]
    t = t.merge(coords, on="city", how="left")
    if t[["lat", "lon"]].isna().any().any():
        raise ValueError("missing coordinates for some cities")

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    pmax = float(max(t["p10"].max(), 0.05))
    sc = ax.scatter(t["lon"], t["lat"], s=45 + 300 * t["p10"] / pmax, c=t["p10"],
                    cmap="YlOrRd", vmin=0, vmax=pmax, edgecolor="k", linewidth=0.6, zorder=4)
    for r in t.itertuples(index=False):
        ax.annotate(r.city, (r.lon, r.lat), fontsize=5.4,
                    xytext=OFFSETS.get(r.city, (4, 3)), textcoords="offset points")
    ax.set_xlabel("Longitude (deg E)")
    ax.set_ylabel("Latitude (deg N)")
    ax.set_title("P(a city exceeds its 1961-2010 daily record within ten years)", fontsize=9)
    ax.set_xlim(84, 130)
    ax.set_ylim(18, 48)
    cb = fig.colorbar(sc, ax=ax, shrink=0.85)
    cb.set_label("$p_{10}$ (L-moment fit)")
    fig.savefig(C.FIGS / "fig14_risk_map.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    top = t.head(10).iloc[::-1]
    ax.barh(range(len(top)), top["p10"], color="#b5342c", alpha=0.8)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([f"{r.city} (RL10={r.rl_10yr:.0f} mm)" for r in top.itertuples()], fontsize=7)
    ax.set_xlabel("$p_{10}$: probability of exceeding the 1961-2010 record by 2035")
    ax.set_title("Top ten cities by ten-year exceedance probability")
    fig.savefig(C.FIGS / "fig15_risk_ranking.png")
    plt.close(fig)
    print("wrote fig14, fig15 from q3_risk_table.csv")


if __name__ == "__main__":
    main()