"""Predictive interface: one distribution object per target.

P3 service duration is the primary target. P2 radial position error is a second
target that exercises the same interface; it is intentionally *not* wired into
the duration model (no measured mapping exists - see design doc, open gap).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .distributions import (
    EmpiricalDistribution,
    GaussianDistribution,
    LogNormalDistribution,
    PredictiveDistribution,
    QuantileDistribution,
)
from .jsonio import DATA
from .types import (
    TARGET_POSITION,
    TARGET_SERVICE,
    PredictiveRequest,
    ReliabilityContext,
)

PREFIX_LADDER = (0.2, 0.6, 1.0)
SCEN_Q = np.linspace(0.05, 0.95, 19)
FACTOR_CAP = 2.5


def reliability_factor(ctx: ReliabilityContext | None, kappa: float = 1.0) -> float:
    """P1 -> Predictive coupling.

    variance multiplier = 1 + kappa * (1-r)/r.  r=1 -> 1.0 exactly, so the
    neutral path reproduces p3_stochastic_schedule bit-for-bit.  r=0.5 ->
    sqrt(2) with kappa=1.  The multiplier is applied to the residual pool, not
    to a fitted Gaussian sigma, so skew and heavy tails survive.
    """
    if ctx is None:
        return 1.0
    if kappa < 0:
        raise ValueError("kappa must be >= 0")
    r = float(np.clip(ctx.r_seg, 1e-3, 1.0))
    return float(min(np.sqrt(1.0 + kappa * (1.0 - r) / r), FACTOR_CAP))


class DurationPredictor:
    """Reads data/p3_duration_predictions.csv (read-only) and rebuilds p3 pools."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.D = Path(data_dir or DATA)
        self.P = pd.read_csv(self.D / "p3_duration_predictions.csv")
        self.index = self.P.set_index(["unit_id", "prefix"])
        tr = self.P[self.P.split == "train"].copy()
        tr["resid"] = tr.duration - tr.pred
        self._tr = tr
        self.RES: dict[tuple[float, str], np.ndarray] = {}
        self.POOL: dict[tuple[float, str], dict[str, Any]] = {}
        for p in PREFIX_LADDER:
            for f in ("A", "L", "P"):
                a = np.sort(tr[(tr.prefix == p) & (tr.family == f)].resid.values)
                if len(a) >= 8:
                    self.RES[(p, f)] = a
                    self.POOL[(p, f)] = {"source": "family", "n": int(len(a))}
                else:
                    pooled = np.sort(tr[tr.prefix == p].resid.values)
                    self.RES[(p, f)] = pooled
                    self.POOL[(p, f)] = {
                        "source": "pooled_prefix",
                        "n": int(len(pooled)),
                        "family_n": int(len(a)),
                    }

    def row(self, unit_id: str, prefix_s: float) -> pd.Series:
        try:
            return self.index.loc[(unit_id, float(prefix_s))]
        except KeyError as exc:
            raise KeyError(f"no prediction row for {unit_id} @ {prefix_s}s") from exc

    def residuals(self, unit_id: str, prefix_s: float, family: str) -> np.ndarray:
        key = (float(prefix_s), str(family))
        if key not in self.RES:
            raise KeyError(f"no residual pool for {key}")
        return self.RES[key]

    def distribution(self, req: PredictiveRequest) -> PredictiveDistribution:
        row = self.row(req.unit_id, req.prefix_s)
        family = str(row.family)
        if req.family and req.family != family:
            raise ValueError(f"family mismatch: request {req.family}, row {family}")
        pred = float(row.pred)
        resid = self.residuals(req.unit_id, req.prefix_s, family)
        factor = reliability_factor(req.reliability, req.kappa)
        prefix = float(req.prefix_s)
        lower = req.alpha * prefix + req.beta
        meta: dict[str, Any] = {
            "unit_id": req.unit_id,
            "family": family,
            "prefix_s": prefix,
            "pred": pred,
            "duration_true_diagnostic": float(row.duration),
            "split": str(row.split),
            "alpha": float(req.alpha),
            "beta": float(req.beta),
            "n_resid": int(len(resid)),
            "residual_pool": self.POOL[(float(req.prefix_s), family)],
            "r_seg": None if req.reliability is None else float(req.reliability.r_seg),
            "kappa": float(req.kappa),
            "reliability_factor": factor,
            "variance_ratio": factor * factor,
            "formula": "alpha*max(prefix, pred + factor*resid) + beta",
            "p3_compatible": bool(abs(factor - 1.0) < 1e-12 and req.n_quantiles == 19),
        }
        if req.representation == "quantile":
            levels = np.linspace(0.05, 0.95, int(req.n_quantiles))
            ds = np.quantile(resid, levels)
            values = req.alpha * np.maximum(prefix, pred + factor * ds) + req.beta
            return QuantileDistribution(
                levels,
                values,
                target=req.target,
                unit="s",
                lower=lower,
                meta=meta,
            )
        if req.representation == "empirical":
            values = req.alpha * np.maximum(prefix, pred + factor * resid) + req.beta
            return EmpiricalDistribution(
                values, target=req.target, unit="s", lower=lower, meta=meta
            )
        if req.representation == "gaussian":
            mu = req.alpha * np.maximum(prefix, pred) + req.beta
            sd = req.alpha * factor * float(np.std(resid, ddof=0))
            meta = dict(meta)
            meta["approximation_note"] = (
                "Gaussian on a heavy-tailed residual pool; q90/median is "
                f"{float(np.quantile(resid, 0.9) / max(np.median(resid), 1e-9)):.2f}, "
                "so the right tail is understated. Diagnostic representation only."
            )
            return GaussianDistribution(mu, max(sd, 1e-6), target=req.target, unit="s", lower=lower, meta=meta)
        raise ValueError(f"unknown representation: {req.representation}")

    def all_representations(self, req: PredictiveRequest) -> dict[str, PredictiveDistribution]:
        out = {}
        for rep in ("quantile", "empirical", "gaussian"):
            r = PredictiveRequest(
                unit_id=req.unit_id,
                family=req.family,
                prefix_s=req.prefix_s,
                target=req.target,
                alpha=req.alpha,
                beta=req.beta,
                reliability=req.reliability,
                kappa=req.kappa,
                representation=rep,
                n_quantiles=req.n_quantiles,
            )
            out[rep] = self.distribution(r)
        return out

    def next_prefix(self, prefix_s: float) -> float | None:
        for p in PREFIX_LADDER:
            if p > float(prefix_s) + 1e-9:
                return float(p)
        return None


class PositionPredictor:
    """P2 radial error distribution from data/p2_interval.json (read-only).

    Published: conformal q90 radius and empirical median. Not published: full
    samples or intermediate quantiles -> `??` (documented, not invented).
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.D = Path(data_dir or DATA)
        self.raw = json.load(open(self.D / "p2_interval.json", encoding="utf-8"))
        self.rows = list(self.raw["by_length"])
        try:
            self.gpu = json.load(open(self.D / "p2_gpu.json", encoding="utf-8"))
        except FileNotFoundError:
            self.gpu = None

    def _row(self, prefix_s: float) -> dict[str, Any]:
        for r in self.rows:
            if abs(float(r["L_s"]) - float(prefix_s)) < 1e-9:
                return r
        raise KeyError(f"no P2 length row at {prefix_s}s")

    def radial(
        self,
        prefix_s: float,
        reliability: ReliabilityContext | None = None,
        kappa: float = 1.0,
        representation: str = "lognormal",
    ) -> PredictiveDistribution:
        row = self._row(prefix_s)
        factor = reliability_factor(reliability, kappa)
        median = float(row["empirical_median_err_m"]) * factor
        q90 = float(row["q90_m"]) * factor
        meta = {
            "prefix_s": float(prefix_s),
            "coverage_test": float(row["coverage_test"]),
            "n_test": int(row["n_test"]),
            "n_val": int(row["n_val"]),
            "source": "data/p2_interval.json by_length",
            "fit_basis": "median + q90 only; intermediate quantiles are ??",
            "reliability_factor": factor,
            "r_seg": None if reliability is None else float(reliability.r_seg),
            "gpu_weights": "PLACEHOLDER (data/p2_gpu.json has metrics only, no .pt)",
        }
        if representation == "lognormal":
            return LogNormalDistribution(
                median, q90, target=TARGET_POSITION, unit="m", lower=0.0, meta=meta
            )
        if representation == "quantile":
            return QuantileDistribution(
                [0.5, 0.9],
                [median, q90],
                target=TARGET_POSITION,
                unit="m",
                lower=0.0,
                meta=meta,
            )
        if representation == "gaussian":
            sigma = q90 / 1.6448536269514722
            meta = dict(meta)
            meta["approximation_note"] = (
                f"Gaussian sigma=q90/1.645; q90/median={q90 / max(median, 1e-12):.2f} "
                "implies a heavier tail than Gaussian."
            )
            return GaussianDistribution(median, max(sigma, 1e-9), target=TARGET_POSITION, unit="m", lower=0.0, meta=meta)
        raise ValueError(f"unknown representation: {representation}")

    def gpu_reference(self) -> dict[str, Any]:
        if not self.gpu:
            return {"status": "PLACEHOLDER", "reason": "data/p2_gpu.json missing"}
        rows = [r for r in self.gpu.get("rows", []) if r.get("variant") == "v2"]
        return {
            "status": "PLACEHOLDER",
            "reason": "train_gpu_p2.py saves metrics only; no .pt checkpoint exists, so per-record forward is impossible",
            "reference_v2_endpoint": rows,
            "source": "data/p2_gpu.json",
        }