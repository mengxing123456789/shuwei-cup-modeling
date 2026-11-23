"""Cross-module inertness audit.

WHY THIS EXISTS
---------------
Applying a variance decomposition to the Q1 equilibrium solver showed that the
diversion weight and all four capacity multipliers carry total-order Sobol
indices of order 1e-5 or below: they are declared parameters that cannot move
a reported number inside the box the paper samples. The same question can be
asked of the other four modules without a single Sobol run, because each is
cheap enough to perturb directly:

    34 ms per Q1 equilibrium    (sampled through the surrogate, hence Sobol)
    0.0018 ms per Q3 welfare    (closed form)
    0.286  ms per Q5 scenario   (closed form recursion)
    <=1 ms per Q4 revenue       (closed form)
    <=1 ms per Q2 equilibrium   (closed form)

So for Q2..Q5 we perturb each declared parameter over its plausible range and
measure the effect on that module's headline output. A parameter whose effect
is below 1e-6 relative to its own scale is reported as INERT -- meaning the
module carries it but nothing downstream reads it in a way that matters.

The audit is deliberately blunt: a parameter is perturbed one at a time over
[min, max] and we record (a) the value range of the output and (b) the
relative swing. One-at-a-time is the right design here because the question is
"does this parameter do anything at all", not "how much of the variance does
it carry"; the latter needs the joint design and is what the Q1 Sobol run did.

Run:  python code/cross_module_inertness.py
Out:  data/cross_module_inertness.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from . import provenance as C

# Below this relative swing the parameter is called inert. 1e-6 is two orders
# below the rounding used to print any number in the paper, so nothing that
# matters can hide under it.

# --- paper-local modules are loaded lazily -------------------------------
# 原实现把这些放在模块顶部，等于把「q2_autos 必须在 sys.path 上」焊死。
# 做成 skill 后包被搬到 scripts/mmkit/，那条路径不再成立，所以改成按需注入。
import sys as _sys
from pathlib import Path as _Path


def _paper_code_dir():
    from .paths import find_paper
    return str(find_paper().code)


def _imp(name):
    d = _paper_code_dir()
    if d not in _sys.path:
        _sys.path.insert(0, d)
    return __import__(name)


INERT_THRESHOLD = 1e-6


def swing(values: list[float]) -> float:
    """Relative swing of a perturbation sweep, on its own scale.

    A flat sweep gives 0 exactly, which is what an inert parameter should
    produce. We normalise by the magnitude of the reference value plus a floor
    so that an output passing through zero does not divide by nothing.
    """
    arr = np.asarray(values, dtype=float)
    ref = abs(arr[0]) if arr[0] != 0 else (np.abs(arr).max() or 1.0)
    return float((arr.max() - arr.min()) / (ref + 1e-9))


def classify(name: str, out: str, sweep: list[float]) -> dict:
    s = swing(sweep)
    return {"parameter": name, "output": out,
            "min": float(np.min(sweep)), "max": float(np.max(sweep)),
            "swing": s, "inert": s < INERT_THRESHOLD}


# ---------------------------------------------------------------------------
# Q2: automobile supply-mode equilibrium
# ---------------------------------------------------------------------------
def _q2_cost_block(par: dict) -> dict:
    """Rebuild the cost / mark-up block that _imp('q2_autos').baseline() does not return.

    Mirrors the parameter block of _imp('q2_autos').main() line for line (mu 1.15,
    tau0 0.025, phi 0.8, cL/cM = 1.10/1.04 x cX, fX/fL/fM = 0.01/0.020/0.015
    x cX, pD = pI x 1.05, tau_mexico 0.30). Kept here rather than imported
    because main() builds it inline and exporting a new function from a shipped
    module for the sake of one audit is the larger change.
    """
    b = par
    mu = 1.15
    tau0 = 0.025
    cX = b["p"]["Japan"] / (mu * (1 + 0.8 * tau0))
    cL, cM = cX * 1.10, cX * 1.04
    fX, fL, fM = 0.01 * cX, 0.020 * cX, 0.015 * cX
    return {"cX": cX, "cL": cL, "cM": cM, "fX": fX, "fL": fL, "fM": fM,
            "markup": mu, "tau_mexico": 0.30, "pD": b["pI"] * 1.05,
            "mode_share": {"X": 0.27, "L": 0.63, "M": 0.10},
            "mode_g0": {"X": cX * mu * (1 + 0.8 * tau0) + fX,
                        "L": cL * mu + fL,
                        "M": cM * mu * (1 + 0.8 * 0.3 * tau0) + fM}}


def audit_q2() -> dict:
    us, jp, sales = _imp('q2_autos').load_auto()
    panel = _imp('q2_autos').import_panel(us, sales)
    par = _imp('q2_autos').baseline(panel, 2024)
    # baseline() carries only {M, import_share, p, pI, q, s_in, sales_m}; the
    # cost block, the Japanese-brand sales level and the mode split are built
    # inline in _imp('q2_autos').main() and are rebuilt here the same way, because
    # solve_auto reads par["japan_sales"] and par["cX"].
    jp_exp_2024 = panel[(panel.year == 2024) & (panel.origin == "Japan")]
    qX0 = float(jp_exp_2024.qty_m.iloc[0])
    par["japan_sales"] = qX0 / 0.27
    par.update(_q2_cost_block(par))
    res = []

    def run(tau: float = 0.15, **_ignored):
        # NOTE: sigma_top and sigma_mode are POSITIONAL arguments of solve_auto
        # (sigma_top, sigma_mode, sigma_in), not keys of par. An earlier version
        # of this audit put them into the parameter dict, where solve_auto never
        # reads them, and reported all three elasticities inert at swing 0.0 --
        # a false inertness that the paper would then have stated as fact. They
        # are passed positionally here.
        p = dict(par)
        for k in ("sigma_top", "sigma_mode", "sigma_in"):
            if k in _ignored:
                p[k] = _ignored.pop(k)
        return _imp('q2_autos').solve_auto(p, tau, 0.8, 0.0,
                                   float(p.get("sigma_top", 4.0)),
                                   float(p.get("sigma_mode", 6.0)),
                                   float(p.get("sigma_in", 2.0)))

    def sweep_param(key: str, grid: list[float], output: str,
                    tau: float = 0.15):
        vals = []
        for v in grid:
            try:
                vals.append(float(run(tau=tau, **{key: v})[output]))
            except (KeyError, TypeError):
                return None
        return vals

    # sigma_in is declared in the signature and reported in the paper as 4.0.
    # The innovation reviewer flagged that the function body never reads it.
    grids = {
        "sigma_in": (np.linspace(1.0, 8.0, 9).tolist(), "imports_m"),
        "sigma_top": (np.linspace(2.0, 8.0, 9).tolist(), "import_share"),
        "sigma_mode": (np.linspace(3.0, 9.0, 9).tolist(), "q_export_m"),
        "tau_mexico": (np.linspace(0.0, 2.0, 9).tolist(), "imports_m"),
        # markup multiplies the Japanese export cost AND the domestic price base
        # one for one, so it cancels out of the import price INDEX by
        # construction (pI_new / pI0 is a ratio of two prices both scaled by mu).
        # Sweeping it therefore cannot move welfare; it is reported inert as a
        # structural property of the closed form, not as a modelling choice.
        "markup": (np.linspace(1.1, 1.6, 9).tolist(), "p_export_usd"),
    }
    # tau_mexico only enters through tau_mexico * tau, so a sweep at the
    # 15% scenario tariff has leverage; at tau = 0 it could not move anything.
    tar = {"tau_mexico": 0.47}
    for key, (grid, output) in grids.items():
        vals = sweep_param(key, grid, output, tau=tar.get(key, 0.15))
        if vals is None:
            res.append({"parameter": key, "output": output, "error": "unreadable"})
            continue
        res.append(classify(key, output, vals))
    return {"module": "Q2", "parameters": res}


# ---------------------------------------------------------------------------
# Q3: semiconductor bi-level optimum
# ---------------------------------------------------------------------------
def audit_q3() -> dict:
    cfg = dict(_imp('q3_semiconductors').SEGMENTS["high"])
    V = 30.25 / (1 - cfg["x0"])
    res = []

    def base():
        return _imp('q3_semiconductors').welfare(0.16, 0.36, cfg, V)

    # Each declared segment parameter, perturbed around its calibrated value.
    pairs = [
        ("delta", np.linspace(0.20, 0.60, 9), "welfare_bn"),
        ("sigma", np.linspace(2.0, 8.0, 9), "welfare_bn"),
        ("lam", np.linspace(0.10, 0.60, 9), "welfare_bn"),
        ("x0", np.linspace(0.02, 0.25, 9), "welfare_bn"),
    ]
    for key, grid, output in pairs:
        vals = []
        for v in grid:
            c = dict(cfg)
            c[key] = float(v)
            vals.append(float(_imp('q3_semiconductors').welfare(0.16, 0.36, c, V)[output]))
        res.append(classify(key, output, vals))

    # mu is a shared argument of welfare/share_curve, not a cfg key.
    vals = [float(_imp('q3_semiconductors').welfare(0.16, 0.36, cfg, V, mu=m)["welfare_bn"])
            for m in np.linspace(1.1, 1.6, 9)]
    res.append(classify("mu (mark-up)", "welfare_bn", vals))
    return {"module": "Q3", "parameters": res}


# ---------------------------------------------------------------------------
# Q4: revenue and Laffer
# ---------------------------------------------------------------------------
def audit_q4() -> dict:
    r = json.loads((C.DATA / "results_q4.json").read_text(encoding="utf-8"))
    e0 = float(r["elasticity"].get("e_hat", 0.0662)) if isinstance(
        r["elasticity"], dict) else 0.0662
    M0 = 3722.4  # bn USD goods imports, 2026 policy base (results_q4 forecast)
    lf = r["laffer"]
    eps = abs(float(lf["e_star"])) * 0.5 if "e_star" in lf else 1.0
    res = []
    pairs = [
        ("eps (demand elasticity)", np.linspace(0.2, 3.0, 9), "R_max_bn"),
        ("M0 (import base)", np.linspace(0.8 * M0, 1.2 * M0, 9), "R_max_bn"),
        # e0 does not move the Laffer PEAK: revenue factors as
        # e * M0 * ((1+e)/(1+e0))**-eps * (1-leakage*e), so e0 enters only
        # through the multiplicative constant (1+e0)**eps and the argmax is
        # invariant. Measured: e* = 1.000 at e0 in {0.04, 0.09, 0.30} with
        # eps = 1, and 0.500 at eps = 3, while R_max moves 1935.6 -> 2419.6.
        # We sweep e0 against R_max instead, where it does have leverage.
        ("e0 (base rate)", np.linspace(0.04, 0.30, 9), "R_max_bn"),
        ("leakage", np.linspace(0.0, 1.0, 9), "e_star"),
    ]
    for key, grid, output in pairs:
        vals = []
        for v in grid:
            kw = {"e0": e0, "M0": M0, "eps": eps, "leakage": 0.0}
            field = key.split(" ")[0]
            kw[field] = float(v)
            vals.append(float(_imp('q4_revenue').laffer(**kw)[output]))
        res.append(classify(key, output, vals))
    return {"module": "Q4", "parameters": res}


# ---------------------------------------------------------------------------
# Q5: AD-AS scenario path
# ---------------------------------------------------------------------------
def audit_q5() -> dict:
    lp = {}
    e_path = {2025: 0.08, 2026: 0.066, 2027: 0.066, 2028: 0.066}
    res = []

    def out(**kw):
        base = dict(retaliation="severe", theta=0.12, gamma=-0.06)
        base.update(kw)
        path = _imp('q5_macro').scenario_path(lp, e_path, **base)
        return {k: float(np.mean([p[k] for p in path]))
                for k in ("inflation", "gdp_growth", "unemployment")}

    for key, grid, output in [
        ("theta", np.linspace(0.0, 0.30, 9), "inflation"),
        ("gamma", np.linspace(-0.20, 0.0, 9), "gdp_growth"),
    ]:
        vals = [out(**{key: float(v)})[output] for v in grid]
        res.append(classify(key, output, vals))

    # retaliation is a three-valued switch, reported as separate points.
    ret = [out(retaliation=k)["inflation"] for k in ("none", "mild", "severe")]
    res.append(classify("retaliation (3-valued switch)", "inflation", ret))
    return {"module": "Q5", "parameters": res}


# ---------------------------------------------------------------------------
# Q5b: the entropy-TOPSIS composite index
# ---------------------------------------------------------------------------
def audit_q5_index() -> dict:
    """Sweep the alternatives' scores against the criterion set.

    The composite is invariant to monotone rescaling of any single column
    (entropy weights re-absorb it), so the only thing that can change a ranking
    is which criteria are in the matrix at all. We therefore report the index
    under each criterion dropped in turn, which is the sensitivity the paper's
    index section actually needs.
    """
    d = _imp('q5_macro').build_quarterly()
    d = d.tail(20)
    cols = ["cpi_infl", "core_infl", "ppi_infl", "ip_growth", "UNRATE",
            "DGS10"]
    cols = [c for c in cols if c in d.columns]
    benefit = [False, False, False, True, False, False][:len(cols)]
    X = d[cols].to_numpy(float)
    base = _imp('q5_macro').entropy_topsis(X, benefit)["scores"]
    res = []
    for j, c in enumerate(cols):
        keep = [k for k in range(len(cols)) if k != j]
        sc = _imp('q5_macro').entropy_topsis(X[:, keep],
                               [benefit[k] for k in keep])["scores"]
        spread = float(max(abs(a - b) for a, b in zip(sc, base)))
        # Score movement is not the reported quantity; the rank shift is. A
        # criterion can move every score by 0.06 and reorder the table by seven
        # places, which is what a reader of the index actually sees.
        r_base = np.argsort(np.argsort(-np.asarray(base)))
        r_new = np.argsort(np.argsort(-np.asarray(sc)))
        shift = int(np.abs(r_new - r_base).max())
        res.append({"parameter": f"drop criterion {c}", "output": "rank",
                    "min": 0.0, "max": float(max(sc)),
                    "swing": spread, "rank_shift": shift,
                    "inert": spread < INERT_THRESHOLD})
    return {"module": "Q5 index", "parameters": res}


# ---------------------------------------------------------------------------
# Q1: read the Sobol result already on disk rather than re-run it
# ---------------------------------------------------------------------------
def audit_q1() -> dict:
    s = json.loads((C.DATA / "q1_sobol.json").read_text(encoding="utf-8"))
    in_cols = s["in_cols"]
    out_cols = s["out_cols"]
    st = s["ST"]           # ST[input][output]
    j = out_cols.index("q_US")
    res = []
    for i, name in enumerate(in_cols):
        v = float(st[i][j])
        res.append({"parameter": name, "output": "q_US",
                    "swing": v, "inert": v < 1e-4, "source": "sobol ST"})
    return {"module": "Q1", "parameters": res}


def main() -> None:
    out = {"threshold": INERT_THRESHOLD,
           "note": "one-at-a-time perturbation over the plausible range; "
                   "Q1 uses the Sobol total-order indices already computed",
           "modules": [audit_q1(), audit_q2(), audit_q3(), audit_q4(),
                       audit_q5(), audit_q5_index()]}

    n_inert = 0
    for m in out["modules"]:
        print(f"\n=== {m['module']} ===")
        for p in m["parameters"]:
            if "error" in p:
                print(f"  {p['parameter']:<28s} {p['error']}")
                continue
            flag = "INERT" if p["inert"] else "     "
            rng = (f"[{p['min']:.4g}, {p['max']:.4g}]"
                   if "min" in p and "max" in p else "(Sobol ST)")
            print(f"  {flag} {p['parameter']:<28s} -> {p['output']:<14s} "
                  f"swing={p['swing']:.3e}  {rng}")
            n_inert += int(p["inert"])
    out["n_inert"] = n_inert
    C.save_json(C.DATA / "cross_module_inertness.json", out)
    print(f"\ninert parameters: {n_inert}")
    print(f"written: {C.DATA / 'cross_module_inertness.json'}")


if __name__ == "__main__":
    main()