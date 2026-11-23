"""Calibrators for P1 frame probabilities and the scores used to choose one.

Fitted on the validation split only. Temperature / isotonic / binned-PAVA are
all monotone, so they cannot improve AUC (it is invariant) - they are selected
on NLL and Brier, which are the scores a probability consumer actually pays.
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score

EPS = 1e-12


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=float)))


def nll(y: Sequence[float], p: Sequence[float]) -> float:
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def brier(y: Sequence[float], p: Sequence[float]) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def ece(y: Sequence[float], p: Sequence[float], bins: int = 10) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1], right=False), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if not np.any(m):
            continue
        total += (m.sum() / len(p)) * abs(float(np.mean(p[m])) - float(np.mean(y[m])))
    return float(total)


def auc(y: Sequence[float], score: Sequence[float]) -> float | None:
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return None
    return float(roc_auc_score(y, np.asarray(score, dtype=float)))


def ap(y: Sequence[float], score: Sequence[float]) -> float | None:
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return None
    return float(average_precision_score(y, np.asarray(score, dtype=float)))


def scorecard(y: Sequence[float], p: Sequence[float]) -> dict[str, Any]:
    return {
        "n": int(len(y)),
        "positives": int(np.sum(np.asarray(y, dtype=int))),
        "nll": nll(y, p),
        "brier": brier(y, p),
        "ece_10": ece(y, p, 10),
        "auc": auc(y, p),
        "ap": ap(y, p),
        "mean_p": float(np.mean(p)),
        "base_rate": float(np.mean(y)),
    }


class Calibrator:
    name = "identity"
    preserves_ranking = True

    def fit(self, p: np.ndarray, y: np.ndarray) -> "Calibrator":
        return self

    def apply(self, p: np.ndarray) -> np.ndarray:
        return np.asarray(p, dtype=float)

    def card(self) -> dict[str, Any]:
        return {"name": self.name, "params": {}}


class PlattCalibrator(Calibrator):
    """Affine logit recalibration p' = sigmoid(a*logit(p)+b), a>0.

    Fitted on validation by NLL. Strictly monotone, so test AUC is unchanged
    from the raw logistic score; unlike temperature-only it can also fix the
    prior shift introduced by class_weight='balanced'.
    """

    name = "platt"
    preserves_ranking = True

    def __init__(self) -> None:
        self.a = 1.0
        self.b = 0.0

    def fit(self, p: np.ndarray, y: np.ndarray) -> "PlattCalibrator":
        z = logit(p)

        def objective(theta: np.ndarray) -> float:
            a = float(np.exp(theta[0]))
            return nll(y, sigmoid(a * z + theta[1]))

        res = minimize(objective, x0=np.array([0.0, 0.0]), method="L-BFGS-B")
        self.a = float(np.exp(res.x[0]))
        self.b = float(res.x[1])
        return self

    def apply(self, p: np.ndarray) -> np.ndarray:
        return sigmoid(self.a * logit(p) + self.b)

    def card(self) -> dict[str, Any]:
        return {"name": self.name, "params": {"a": self.a, "b": self.b}}


class TemperatureCalibrator(Calibrator):
    name = "temperature"
    preserves_ranking = True

    def __init__(self) -> None:
        self.temperature = 1.0

    def fit(self, p: np.ndarray, y: np.ndarray) -> "TemperatureCalibrator":
        z = logit(p)

        def objective(u: float) -> float:
            return nll(y, sigmoid(z / np.exp(u)))

        res = minimize_scalar(objective, bounds=(-3.0, 3.0), method="bounded")
        self.temperature = float(np.exp(res.x))
        return self

    def apply(self, p: np.ndarray) -> np.ndarray:
        return sigmoid(logit(p) / self.temperature)

    def card(self) -> dict[str, Any]:
        return {"name": self.name, "params": {"temperature": self.temperature}}


class IsotonicCalibrator(Calibrator):
    name = "isotonic"
    preserves_ranking = False

    def __init__(self) -> None:
        self.model: IsotonicRegression | None = None

    def fit(self, p: np.ndarray, y: np.ndarray) -> "IsotonicCalibrator":
        self.model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.model.fit(p, y)
        return self

    def apply(self, p: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("calibrator not fitted")
        return np.clip(self.model.predict(np.asarray(p, dtype=float)), 0.0, 1.0)

    def card(self) -> dict[str, Any]:
        knots = []
        if self.model is not None:
            xs = np.atleast_1d(self.model.X_thresholds_)
            ys = np.atleast_1d(self.model.y_thresholds_)
            step = max(1, len(xs) // 20)
            knots = [{"x": float(a), "y": float(b)} for a, b in zip(xs[::step], ys[::step])]
        return {
            "name": self.name,
            "params": {
                "n_knots": 0 if self.model is None else int(len(np.atleast_1d(self.model.X_thresholds_))),
                "sampled_knots": knots,
            },
        }


def _pava(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    blocks: list[list[float]] = []
    for i in range(len(values)):
        blocks.append([i, i, float(values[i]), float(weights[i])])
        while len(blocks) > 1 and blocks[-2][2] > blocks[-1][2]:
            b = blocks.pop()
            a = blocks.pop()
            w = a[3] + b[3]
            blocks.append([a[0], b[1], (a[2] * a[3] + b[2] * b[3]) / w, w])
    out = np.empty(len(values), dtype=float)
    for s, e, v, _ in blocks:
        out[int(s) : int(e) + 1] = v
    return out


class BinnedCalibrator(Calibrator):
    name = "binned_pava"
    preserves_ranking = False

    def __init__(self, bins: int = 20) -> None:
        self.bins = int(bins)
        self.edges: np.ndarray | None = None
        self.values: np.ndarray | None = None

    def fit(self, p: np.ndarray, y: np.ndarray) -> "BinnedCalibrator":
        p = np.asarray(p, dtype=float)
        y = np.asarray(y, dtype=float)
        self.edges = np.quantile(p, np.linspace(0.0, 1.0, self.bins + 1))
        self.edges[0] = -np.inf
        self.edges[-1] = np.inf
        idx = np.clip(np.digitize(p, self.edges[1:-1], right=False), 0, self.bins - 1)
        sums = np.bincount(idx, weights=y, minlength=self.bins)
        counts = np.bincount(idx, minlength=self.bins).astype(float)
        raw = np.divide(sums, np.maximum(counts, 1.0))
        self.values = _pava(raw, np.maximum(counts, 1.0))
        return self

    def apply(self, p: np.ndarray) -> np.ndarray:
        if self.edges is None or self.values is None:
            raise RuntimeError("calibrator not fitted")
        idx = np.clip(np.digitize(np.asarray(p, dtype=float), self.edges[1:-1], right=False), 0, self.bins - 1)
        return np.clip(self.values[idx], 0.0, 1.0)

    def card(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "params": {
                "bins": self.bins,
                "values": [float(v) for v in (self.values if self.values is not None else [])],
            },
        }


def fit_calibrators(p: np.ndarray, y: np.ndarray) -> list[Calibrator]:
    return [
        IsotonicCalibrator().fit(p, y),
        TemperatureCalibrator().fit(p, y),
        PlattCalibrator().fit(p, y),
        BinnedCalibrator(20).fit(p, y),
        Calibrator().fit(p, y),
    ]


def choose_calibrator(
    p: np.ndarray, y: np.ndarray
) -> tuple[Calibrator, list[dict[str, Any]]]:
    """Fit all five, score them on the same split, pick lowest NLL.

    Hard constraint: the selected calibrator must be strictly monotone
    (identity / temperature / Platt). Isotonic and binned-PAVA are reported for
    transparency but not selected, because their plateaus tie distant scores and
    measurably reduce test AUC of the fused trust (0.6096 vs 0.6267 in the first
    run of this module). For a probability that feeds a ranking-sensitive fusion
    this is a correctness constraint, not a preference.
    """
    fitted = fit_calibrators(p, y)
    rows = []
    for c in fitted:
        q = c.apply(p)
        row = scorecard(y, q)
        row["name"] = c.name
        row["preserves_ranking"] = bool(c.preserves_ranking)
        rows.append(row)
    eligible = [r for r in rows if r["preserves_ranking"]]
    best = min(eligible or rows, key=lambda r: r["nll"])
    chosen = next(c for c in fitted if c.name == best["name"])
    return chosen, rows