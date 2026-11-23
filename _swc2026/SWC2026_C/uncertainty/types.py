"""Explicit data types shared by the three U-layer interfaces.

No module-level mutable state: every hand-off is one of these objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

PREFIX_LADDER = (0.2, 0.6, 1.0)
TARGET_SERVICE = "service_duration_s"
TARGET_POSITION = "radial_position_error_m"


@dataclass(frozen=True)
class FrameWindow:
    """Half-open frame window [start, end) inside one panel record."""

    record_id: int
    start: int
    end: int
    fps: float = 30.0

    def __post_init__(self) -> None:
        if self.record_id < 0:
            raise ValueError("record_id must be >= 0")
        if self.start < 0 or self.end <= self.start:
            raise ValueError(f"invalid window [{self.start},{self.end})")
        if self.fps <= 0:
            raise ValueError("fps must be positive")

    @property
    def n_frames(self) -> int:
        return self.end - self.start

    @property
    def duration_s(self) -> float:
        return self.n_frames / float(self.fps)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "start": self.start,
            "end": self.end,
            "n_frames": self.n_frames,
            "fps": self.fps,
            "duration_s": self.duration_s,
        }


@dataclass(frozen=True)
class FrameReliability:
    """Per-frame output of the P1 interface for one hand."""

    record_id: int
    hand: str
    frame_index: np.ndarray          # global row indices into panel.npz
    p_bad_raw: np.ndarray            # logistic score before calibration
    p_bad: np.ndarray                # calibrated P(annotated bad frame)
    r_geo: np.ndarray                # geometric (Mahalanobis) trust
    r: np.ndarray                    # fused trust = 0.5*(1-p_bad)+0.5*r_geo
    calibrator: str
    source: str
    placeholder: bool = False
    meta: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "hand": self.hand,
            "calibrator": self.calibrator,
            "source": self.source,
            "placeholder": self.placeholder,
            "n_frames": int(len(self.frame_index)),
            "p_bad_raw_mean": float(np.mean(self.p_bad_raw)) if len(self.p_bad_raw) else None,
            "p_bad_mean": float(np.mean(self.p_bad)) if len(self.p_bad) else None,
            "r_geo_mean": float(np.mean(self.r_geo)) if len(self.r_geo) else None,
            "r_mean": float(np.mean(self.r)) if len(self.r) else None,
            "frames": [
                {
                    "frame": int(i),
                    "p_bad_raw": float(a),
                    "p_bad": float(b),
                    "r_geo": float(c),
                    "r": float(d),
                }
                for i, a, b, c, d in zip(
                    self.frame_index, self.p_bad_raw, self.p_bad, self.r_geo, self.r
                )
            ],
        }


@dataclass(frozen=True)
class SegmentReliability:
    """Frame-level trust aggregated to one segment/window for one hand."""

    record_id: int
    hand: str
    start: int
    end: int
    fps: float
    r_seg: float
    r_mean: float
    r_geo: float
    r_min: float
    p_bad_seg: float
    p_any_bad_indep: float
    p_any_bad_eff: float
    n_frames: int
    n_eff: float
    aggregation: str
    calibrator: str
    source: str
    placeholder: bool = False
    meta: Mapping[str, Any] = field(default_factory=dict)

    def as_context(self) -> "ReliabilityContext":
        return ReliabilityContext(
            r_seg=float(self.r_seg),
            hand=self.hand,
            record_id=self.record_id,
            n_frames=self.n_frames,
            n_eff=float(self.n_eff),
            aggregation=self.aggregation,
            calibrator=self.calibrator,
            source=self.source,
            placeholder=self.placeholder,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "hand": self.hand,
            "start": self.start,
            "end": self.end,
            "n_frames": self.n_frames,
            "r_seg": self.r_seg,
            "r_mean": self.r_mean,
            "r_geo": self.r_geo,
            "r_min": self.r_min,
            "p_bad_seg": self.p_bad_seg,
            "p_any_bad_indep": self.p_any_bad_indep,
            "p_any_bad_eff": self.p_any_bad_eff,
            "n_eff": self.n_eff,
            "aggregation": self.aggregation,
            "calibrator": self.calibrator,
            "source": self.source,
            "placeholder": self.placeholder,
            "meta": dict(self.meta),
        }


@dataclass(frozen=True)
class ReliabilityContext:
    """The scalar P1 -> Predictive coupling object. No other channel is implicit."""

    r_seg: float
    hand: str
    record_id: int
    n_frames: int
    n_eff: float
    aggregation: str
    calibrator: str
    source: str
    placeholder: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.r_seg <= 1.0):
            raise ValueError(f"r_seg outside [0,1]: {self.r_seg}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "r_seg": self.r_seg,
            "hand": self.hand,
            "record_id": self.record_id,
            "n_frames": self.n_frames,
            "n_eff": self.n_eff,
            "aggregation": self.aggregation,
            "calibrator": self.calibrator,
            "source": self.source,
            "placeholder": self.placeholder,
        }


@dataclass(frozen=True)
class PredictiveRequest:
    """Everything Predictive.distribution() is allowed to see."""

    unit_id: str
    family: str
    prefix_s: float
    target: str = TARGET_SERVICE
    alpha: float = 1.0
    beta: float = 0.5
    reliability: ReliabilityContext | None = None
    kappa: float = 1.0
    representation: str = "quantile"   # quantile | empirical | gaussian
    n_quantiles: int = 19


@dataclass(frozen=True)
class StepReport:
    """One timed step of the smoke chain."""

    name: str
    ms: float
    stats: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ms": self.ms, "stats": dict(self.stats)}


def aggregate_frames(
    r: Sequence[float],
    p_bad: Sequence[float],
    method: str = "geometric",
    ar1_rho: float = 0.6,
    eps: float = 1e-6,
) -> dict[str, float]:
    """Aggregate frame trust to a segment without hiding the choice.

    r_seg is a *frame-level* probability, so it stays in [0,1] and is directly
    comparable across window lengths. n_eff is an AR(1) effective sample size;
    p_any_bad_eff uses it to avoid pretending 30 frames are 30 independent draws.
    """
    r = np.asarray(r, dtype=float)
    p = np.asarray(p_bad, dtype=float)
    if r.size == 0:
        raise ValueError("empty frame window")
    n = int(r.size)
    r_mean = float(np.mean(r))
    r_geo = float(np.exp(np.mean(np.log(np.clip(r, eps, 1.0)))))
    r_min = float(np.min(r))
    p_mean = float(np.mean(p))
    p_any_indep = float(1.0 - np.prod(1.0 - np.clip(p, 0.0, 1.0)))
    n_eff = float(1.0 + (n - 1) * (1.0 - ar1_rho) / (1.0 + ar1_rho))
    p_any_bad_eff = float(1.0 - (1.0 - p_mean) ** n_eff)
    if method == "mean":
        r_seg = r_mean
    elif method == "geometric":
        r_seg = r_geo
    elif method == "min":
        r_seg = r_min
    elif method == "conservative":
        r_seg = min(r_mean, r_geo)
    else:
        raise ValueError(f"unknown aggregation: {method}")
    return {
        "r_seg": float(np.clip(r_seg, 0.0, 1.0)),
        "r_mean": r_mean,
        "r_geo": r_geo,
        "r_min": r_min,
        "p_bad_seg": p_mean,
        "p_any_bad_indep": p_any_indep,
        "p_any_bad_eff": p_any_bad_eff,
        "n_frames": n,
        "n_eff": n_eff,
        "aggregation": method,
        "ar1_rho": ar1_rho,
    }