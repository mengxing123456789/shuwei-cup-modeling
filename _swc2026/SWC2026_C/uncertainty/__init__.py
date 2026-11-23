"""Track U: one probability chain for P1 -> P2 -> P3.

Public surface
--------------
types          explicit dataclasses passed between layers
distributions  quantile / empirical / Gaussian / log-normal predictive objects
calibration    temperature / isotonic / binned calibrators + proper scores
reliability    P1 frame-level calibrated trust -> segment-level reliability
predictive     P2 position error + P3 service-duration predictive distributions
decision       distribution-only scheduler + value-of-information
consistency    numeric alignment against code/p3_stochastic_schedule.py
smoke          one-record end-to-end runner (writes data/uncertainty_smoke.json)
"""

__all__ = [
    "types",
    "distributions",
    "calibration",
    "reliability",
    "predictive",
    "decision",
    "consistency",
    "smoke",
]