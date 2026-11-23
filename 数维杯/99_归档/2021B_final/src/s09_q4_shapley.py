#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q4 upgrade: Shapley decomposition of the Zhengzhou/Shanxi loss gap.

The Task 4 loss comparison is an identity, not a causal model:

    loss ratio = density ratio x affected-share ratio x loss-per-affected ratio x area ratio

Any factor can be "blamed" by holding the others fixed, and the answer depends on the
order in which factors are switched. A Shapley value averages over all orderings; for a
multiplicative identity it collapses to the log-share, which is what this script reports,
together with single-factor-removal counterfactuals.

Outputs
-------
q4_shapley.json
fig24_q4_shapley.png
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import common as C

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "grid.linestyle": ":"})

# official figures, see s05_q4.py for the sources
EV = {
    "Zhengzhou": {"loss": 409.0e8, "area": 7567.0, "pop": 12.60e6, "affected": None},
    "Henan": {"loss": 1200.6e8, "area": 167000.0, "pop": 99.37e6, "affected": 1478.6e4},
    "Shanxi": {"loss": 50.29e8, "area": 156700.0, "pop": 34.80e6, "affected": 175.71e4},
}


def factors(a: dict, b: dict) -> dict:
    """Ratios a/b for the four multiplicative factors."""
    dens = (a["pop"] / a["area"]) / (b["pop"] / b["area"])
    share = (a["affected"] / a["pop"]) / (b["affected"] / b["pop"])
    sev = (a["loss"] / a["affected"]) / (b["loss"] / b["affected"])
    area = a["area"] / b["area"]
    return {"density": dens, "affected share": share, "loss per affected": sev, "area": area}


def main() -> None:
    fa = factors(EV["Henan"], EV["Shanxi"])
    ratio = EV["Henan"]["loss"] / EV["Shanxi"]["loss"]
    prod = float(np.prod(list(fa.values())))
    logs = {k: math.log(v) for k, v in fa.items()}
    total_log = math.log(ratio)

    # Shapley over the multiplicative game: v(S) = product of the factors in S
    names = list(fa)
    shap = {k: 0.0 for k in names}
    for k in names:
        others = [n for n in names if n != k]
        for r in range(len(others) + 1):
            for subset in itertools.combinations(others, r):
                w = math.factorial(len(subset)) * math.factorial(len(names) - len(subset) - 1) \
                    / math.factorial(len(names))
                v_with = math.prod([fa[n] for n in subset] + [fa[k]])
                v_without = math.prod([fa[n] for n in subset])
                shap[k] += w * (v_with - v_without)

    # single-factor removal counterfactuals
    removal = {k: ratio / v for k, v in fa.items()}

    out = {
        "events": EV,
        "factors": fa,
        "product_of_factors": prod,
        "loss_ratio": ratio,
        "identity_error": abs(prod - ratio),
        "log_shares": {k: v / total_log for k, v in logs.items()},
        "shapley_level_cny": shap,
        "shapley_share": {k: v / (ratio - 1.0) for k, v in shap.items()},
        "single_factor_removal_ratio": removal,
        "note": "Shapley over the four multiplicative factors, Henan/Shanxi, with v(S) = product "
                "of the factors in S and the worth of the grand coalition normalised to the loss "
                "ratio. The two share columns answer different questions and are NOT equal: the "
                "log-share splits the log of the gap (a ratio decomposition, additive in logs), "
                "while shapley_share splits the gap itself in level terms. The text quotes "
                "shapley_share; the figure plots the same column.",
    }
    (C.RESULTS / "q4_shapley.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(4.9, 2.6))
    keys = list(fa)
    vals = [out["shapley_share"][k] * 100 for k in keys]
    ax.barh(keys[::-1], vals[::-1], color="#2f6f9f", height=0.55)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.6, i, f"{v:.1f}%", va="center", fontsize=8)
    ax.set_xlabel("Share of the 23.9-fold loss gap (%)")
    ax.set_title("Shapley decomposition, Henan/Shanxi")
    ax.set_xlim(0, max(vals) * 1.25)
    fig.savefig(C.FIGS / "fig24_q4_shapley.png")
    plt.close(fig)

    print(json.dumps({k: out[k] for k in ("factors", "loss_ratio", "identity_error",
                                          "log_shares", "shapley_share",
                                          "single_factor_removal_ratio")}, indent=1))
    print("loss ratio", round(ratio, 3), "product", round(prod, 3))


if __name__ == "__main__":
    main()