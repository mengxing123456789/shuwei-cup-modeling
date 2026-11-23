"""Predictive distributions the scheduler is allowed to consume.

All four representations expose the same read-only surface:
cdf(x), survival(x), quantile(q), mean(), sd(), sample(n), summary().
`kind` records which representation was actually used; none of them is
silently converted to a point estimate.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import norm


class PredictiveDistribution:
    kind = "base"

    def __init__(
        self,
        target: str,
        unit: str,
        lower: float | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> None:
        self.target = target
        self.unit = unit
        self.lower = None if lower is None else float(lower)
        self.meta: dict[str, Any] = dict(meta or {})

    # -- required ---------------------------------------------------------
    def cdf(self, x: float | np.ndarray) -> float | np.ndarray:
        raise NotImplementedError

    def quantile(self, q: float | np.ndarray) -> float | np.ndarray:
        raise NotImplementedError

    def mean(self) -> float:
        raise NotImplementedError

    def sd(self) -> float:
        raise NotImplementedError

    def sample(self, n: int, rng: np.random.Generator | None = None) -> np.ndarray:
        raise NotImplementedError

    # -- shared -----------------------------------------------------------
    def survival(self, x: float | np.ndarray) -> float | np.ndarray:
        return 1.0 - self.cdf(x)

    def cdf_many(self, xs: Sequence[float]) -> list[float]:
        v = np.atleast_1d(self.cdf(np.asarray(xs, dtype=float)))
        return [float(a) for a in v]

    def summary(self, probs: Sequence[float] = (0.05, 0.1, 0.5, 0.9, 0.95)) -> dict[str, Any]:
        qs = {f"q{int(round(p * 100)):02d}": float(np.asarray(self.quantile(p))) for p in probs}
        return {
            "kind": self.kind,
            "target": self.target,
            "unit": self.unit,
            "lower": self.lower,
            "mean": float(self.mean()),
            "sd": float(self.sd()),
            "quantiles": qs,
            "meta": dict(self.meta),
        }


class EmpiricalDistribution(PredictiveDistribution):
    kind = "empirical"

    def __init__(
        self,
        samples: Sequence[float],
        weights: Sequence[float] | None = None,
        target: str = "",
        unit: str = "",
        lower: float | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(target, unit, lower, meta)
        s = np.asarray(samples, dtype=float).ravel()
        if s.size == 0:
            raise ValueError("empty sample set")
        order = np.argsort(s, kind="mergesort")
        self.samples = s[order]
        if weights is None:
            w = np.full(s.size, 1.0 / s.size)
        else:
            w = np.asarray(weights, dtype=float).ravel()[order]
            if w.size != s.size or np.any(w < 0):
                raise ValueError("weights must match samples and be non-negative")
            w = w / w.sum()
        self.weights = w
        self._cum = np.cumsum(w)
        self._cum[-1] = 1.0

    def cdf(self, x: float | np.ndarray) -> float | np.ndarray:
        scalar = np.isscalar(x)
        xs = np.atleast_1d(np.asarray(x, dtype=float))
        idx = np.searchsorted(self.samples, xs, side="right")
        out = np.zeros(xs.shape, dtype=float)
        mask = idx > 0
        out[mask] = self._cum[idx[mask] - 1]
        if self.lower is not None:
            out = np.where(xs < self.lower, 0.0, out)
        out = np.clip(out, 0.0, 1.0)
        return float(out[0]) if scalar else out

    def quantile(self, q: float | np.ndarray) -> float | np.ndarray:
        # np.quantile matches p3_stochastic_schedule.quant(); weights are equal
        # for every distribution this project emits, so the two agree exactly.
        out = np.quantile(self.samples, q)
        return float(out) if np.isscalar(q) else out

    def mean(self) -> float:
        return float(np.sum(self.samples * self.weights))

    def sd(self) -> float:
        mu = self.mean()
        return float(np.sqrt(np.sum(self.weights * (self.samples - mu) ** 2)))

    def sample(self, n: int, rng: np.random.Generator | None = None) -> np.ndarray:
        rng = rng or np.random.default_rng()
        return rng.choice(self.samples, size=n, p=self.weights)


class QuantileDistribution(EmpiricalDistribution):
    """A finite quantile grid treated as equiprobable atoms.

    This is deliberately the same semantics p3_stochastic_schedule uses:
    on-probability = mean(scenario <= due). Interpolating the quantile function
    would *not* reproduce the shipped scheduler, so the stored `levels` are
    documentation + a handle for re-weighting, not an interpolation rule.
    """

    kind = "quantile"

    def __init__(
        self,
        levels: Sequence[float],
        values: Sequence[float],
        target: str = "",
        unit: str = "",
        lower: float | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> None:
        lev = np.asarray(levels, dtype=float).ravel()
        val = np.asarray(values, dtype=float).ravel()
        if lev.size != val.size or lev.size == 0:
            raise ValueError("levels and values must have the same non-zero length")
        if np.any(np.diff(lev) < 0):
            raise ValueError("levels must be non-decreasing")
        m = dict(meta or {})
        m["levels"] = [float(v) for v in lev]
        m["n_atoms"] = int(lev.size)
        super().__init__(val, target=target, unit=unit, lower=lower, meta=m)
        self.levels = lev


class GaussianDistribution(PredictiveDistribution):
    kind = "gaussian"

    def __init__(
        self,
        mu: float,
        sd: float,
        target: str = "",
        unit: str = "",
        lower: float | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(target, unit, lower, meta)
        if sd <= 0:
            raise ValueError("sd must be positive")
        self.mu = float(mu)
        self.sigma = float(sd)
        self._z0 = None if lower is None else (float(lower) - self.mu) / self.sigma
        self._mass = 1.0 if self._z0 is None else float(1.0 - norm.cdf(self._z0))
        if self._mass <= 1e-12:
            raise ValueError("truncation leaves no probability mass")

    def cdf(self, x: float | np.ndarray) -> float | np.ndarray:
        scalar = np.isscalar(x)
        xs = np.atleast_1d(np.asarray(x, dtype=float))
        num = norm.cdf((xs - self.mu) / self.sigma)
        if self._z0 is not None:
            num = num - norm.cdf(self._z0)
            num = np.where(xs < float(self.lower), 0.0, num)
        out = np.clip(num / self._mass, 0.0, 1.0)
        return float(out[0]) if scalar else out

    def quantile(self, q: float | np.ndarray) -> float | np.ndarray:
        scalar = np.isscalar(q)
        qs = np.atleast_1d(np.asarray(q, dtype=float))
        base = 0.0 if self._z0 is None else float(norm.cdf(self._z0))
        z = norm.ppf(np.clip(base + qs * self._mass, 1e-12, 1 - 1e-12))
        out = self.mu + self.sigma * z
        return float(out[0]) if scalar else out

    def mean(self) -> float:
        if self._z0 is None:
            return self.mu
        pdf = float(norm.pdf(self._z0))
        return float(self.mu + self.sigma * pdf / self._mass)

    def sd(self) -> float:
        if self._z0 is None:
            return self.sigma
        pdf = float(norm.pdf(self._z0))
        var = self.sigma**2 * (1.0 + self._z0 * pdf / self._mass - (pdf / self._mass) ** 2)
        return float(np.sqrt(max(var, 0.0)))

    def sample(self, n: int, rng: np.random.Generator | None = None) -> np.ndarray:
        rng = rng or np.random.default_rng()
        if self._z0 is None:
            return rng.normal(self.mu, self.sigma, size=n)
        base = float(norm.cdf(self._z0))
        u = base + rng.random(n) * self._mass
        return self.mu + self.sigma * norm.ppf(u)


class LogNormalDistribution(PredictiveDistribution):
    """Two-quantile log-normal fit; used only for P2 radial error.

    p2_interval.json publishes median and q90, not a full sample. A Gaussian
    cannot reproduce q90/median = 5.03 at 0.2 s (chi-3 would give 1.63), so the
    log-normal is the least-assumption representation that hits both published
    numbers. Intermediate quantiles remain an assumption, not a measurement.
    """

    kind = "lognormal"

    def __init__(
        self,
        median: float,
        q90: float,
        target: str = "",
        unit: str = "m",
        lower: float = 0.0,
        meta: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(target, unit, lower, meta)
        if median <= 0 or q90 <= median:
            raise ValueError("require 0 < median < q90")
        self.median = float(median)
        self.q90 = float(q90)
        self.mu_log = float(np.log(median))
        self.sigma_log = float((np.log(q90) - np.log(median)) / norm.ppf(0.90))

    def cdf(self, x: float | np.ndarray) -> float | np.ndarray:
        scalar = np.isscalar(x)
        xs = np.atleast_1d(np.asarray(x, dtype=float))
        out = np.where(
            xs <= 0,
            0.0,
            norm.cdf((np.log(np.maximum(xs, 1e-300)) - self.mu_log) / self.sigma_log),
        )
        return float(out[0]) if scalar else out

    def quantile(self, q: float | np.ndarray) -> float | np.ndarray:
        out = np.exp(self.mu_log + self.sigma_log * norm.ppf(np.asarray(q, dtype=float)))
        return float(out) if np.isscalar(q) else out

    def mean(self) -> float:
        return float(np.exp(self.mu_log + 0.5 * self.sigma_log**2))

    def sd(self) -> float:
        m = self.mean()
        return float(np.sqrt((np.exp(self.sigma_log**2) - 1.0) * m**2))

    def sample(self, n: int, rng: np.random.Generator | None = None) -> np.ndarray:
        rng = rng or np.random.default_rng()
        return rng.lognormal(self.mu_log, self.sigma_log, size=n)