"""Decision interface: the scheduler sees distributions, never point estimates.

The single-job decision mirrors the *corrected* protocol in
code/p3_stochastic_schedule.py:
    service p = alpha*d + beta, completion C = start + p
    reservation b = max(reserve_min, quantile_q(p))
    q = clip(0.70 - 0.55*max(0, pressure-0.75), 0.35, 0.70)
    pressure = remaining_work / max(H - now, eps)
VoI mirrors its review branch: one extra observation costs one second of delay
plus one unit of observation cost, combined shadow price 0.02.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from .distributions import PredictiveDistribution


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    case_id: str
    family: str
    release_s: float
    due_s: float
    weight: float
    zone: str
    duration_true_s: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "case_id": self.case_id,
            "family": self.family,
            "release_s": self.release_s,
            "due_s": self.due_s,
            "weight": self.weight,
            "zone": self.zone,
            "duration_true_s": self.duration_true_s,
        }


@dataclass(frozen=True)
class ScheduleContext:
    now_s: float
    horizon_s: float
    budget_s: float
    spent_s: float = 0.0
    current_zone: str = "Z0"
    alpha: float = 1.0
    beta: float = 0.5
    reserve_min: float = 0.2
    speed: float = 1.0
    changeover_s: float = 0.5
    review_delay_s: float = 1.0
    review_cost_s: float = 1.0
    shadow_price: float = 0.02
    pressure_override: float | None = None
    zones: Mapping[str, tuple[float, float]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "now_s": self.now_s,
            "horizon_s": self.horizon_s,
            "budget_s": self.budget_s,
            "spent_s": self.spent_s,
            "current_zone": self.current_zone,
            "alpha": self.alpha,
            "beta": self.beta,
            "reserve_min": self.reserve_min,
            "speed": self.speed,
            "changeover_s": self.changeover_s,
            "review_delay_s": self.review_delay_s,
            "review_cost_s": self.review_cost_s,
            "shadow_price": self.shadow_price,
            "pressure_override": self.pressure_override,
            "zones": {k: list(v) for k, v in self.zones.items()},
        }


@dataclass(frozen=True)
class ScheduleDecision:
    action: str
    start_s: float
    expected_completion_s: float
    p_on_time: float
    reserve_s: float
    q_level: float
    pressure: float
    slack_s: float
    score: float
    distribution_kind: str
    distribution_mean_s: float
    distribution_sd_s: float
    reason: str
    feasible: bool
    meta: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "start_s": self.start_s,
            "expected_completion_s": self.expected_completion_s,
            "p_on_time": self.p_on_time,
            "reserve_s": self.reserve_s,
            "q_level": self.q_level,
            "pressure": self.pressure,
            "slack_s": self.slack_s,
            "score": self.score,
            "distribution_kind": self.distribution_kind,
            "distribution_mean_s": self.distribution_mean_s,
            "distribution_sd_s": self.distribution_sd_s,
            "reason": self.reason,
            "feasible": self.feasible,
            "meta": dict(self.meta),
        }


@dataclass(frozen=True)
class VoIReport:
    p0: float
    p1: float | None
    delta_p: float | None
    weighted_gain: float | None
    delay_s: float
    cost_s: float
    shadow_price: float
    cost_equiv: float
    net_value: float | None
    decided: bool
    basis: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "p0": self.p0,
            "p1": self.p1,
            "delta_p": self.delta_p,
            "weighted_gain": self.weighted_gain,
            "delay_s": self.delay_s,
            "cost_s": self.cost_s,
            "shadow_price": self.shadow_price,
            "cost_equiv": self.cost_equiv,
            "net_value": self.net_value,
            "decided": self.decided,
            "basis": self.basis,
        }


def travel_time(z0: str, z1: str, zones: Mapping[str, tuple[float, float]], speed: float = 1.0) -> float:
    if z0 == z1:
        return 0.0
    if z0 not in zones or z1 not in zones:
        raise KeyError(f"unknown zone: {z0} -> {z1}")
    d = math.hypot(zones[z0][0] - zones[z1][0], zones[z0][1] - zones[z1][1])
    return d / max(float(speed), 1e-9)


def capacity_pressure(
    preds_s: list[float] | np.ndarray,
    alpha: float,
    beta: float,
    horizon_s: float,
    now_s: float,
    plus_per_job: float = 1.0,
) -> float:
    rem = float(np.sum(np.asarray(preds_s, dtype=float) * alpha + beta + plus_per_job))
    return rem / max(float(horizon_s) - float(now_s), 1e-6)


class Decider:
    def q_level(self, pressure: float) -> float:
        return float(np.clip(0.70 - 0.55 * max(0.0, pressure - 0.75), 0.35, 0.70))

    def decide(
        self,
        job: JobSpec,
        dist: PredictiveDistribution,
        ctx: ScheduleContext,
        pressure: float | None = None,
    ) -> ScheduleDecision:
        travel = travel_time(ctx.current_zone, job.zone, ctx.zones, ctx.speed)
        change = 0.0 if ctx.current_zone == job.zone else ctx.changeover_s
        start = max(float(ctx.now_s), float(job.release_s)) + travel + change
        mean = float(dist.mean())
        sd = float(dist.sd())
        pr = (
            float(ctx.pressure_override)
            if ctx.pressure_override is not None
            else float(pressure)
            if pressure is not None
            else (mean + 1.0) / max(ctx.horizon_s - ctx.now_s, 1e-6)
        )
        q = self.q_level(pr)
        reserve = max(float(ctx.reserve_min), float(dist.quantile(q)))
        p_on = float(dist.cdf(job.due_s - start))
        expected = start + mean
        slack = float(job.due_s) - expected
        overtime = max(0.0, expected - float(job.due_s))
        score = float(job.weight) * p_on - float(job.weight) * overtime / max(float(job.due_s), 1.0)
        feasible = bool(start + reserve <= ctx.horizon_s and ctx.spent_s + mean <= ctx.budget_s)
        if not feasible:
            action = "defer"
            reason = (
                "insufficient horizon" if start + reserve > ctx.horizon_s else "insufficient budget"
            )
        else:
            action = "execute"
            reason = "distribution mean fits budget and reservation fits horizon"
        return ScheduleDecision(
            action=action,
            start_s=float(start),
            expected_completion_s=float(expected),
            p_on_time=p_on,
            reserve_s=float(reserve),
            q_level=float(q),
            pressure=float(pr),
            slack_s=float(slack),
            score=float(score),
            distribution_kind=dist.kind,
            distribution_mean_s=mean,
            distribution_sd_s=sd,
            reason=reason,
            feasible=feasible,
            meta={
                "travel_s": travel,
                "changeover_s": change,
                "family": job.family,
                "alpha": ctx.alpha,
                "beta": ctx.beta,
                "pressure_mode": "override" if ctx.pressure_override is not None else ("case" if pressure is not None else "single_job"),
                "distribution_target": dist.target,
            },
        )

    def voi(
        self,
        job: JobSpec,
        d0: PredictiveDistribution,
        d1: PredictiveDistribution | None,
        start0: float,
        ctx: ScheduleContext,
    ) -> VoIReport:
        p0 = float(d0.cdf(job.due_s - start0))
        delay = float(ctx.review_delay_s)
        cost_equiv = float(ctx.shadow_price) * (delay + float(ctx.review_cost_s))
        if d1 is None:
            return VoIReport(
                p0=p0,
                p1=None,
                delta_p=None,
                weighted_gain=None,
                delay_s=delay,
                cost_s=float(ctx.review_cost_s),
                shadow_price=float(ctx.shadow_price),
                cost_equiv=cost_equiv,
                net_value=None,
                decided=False,
                basis="no later prefix available; VoI undefined",
            )
        p1 = float(d1.cdf(job.due_s - (start0 + delay)))
        delta = p1 - p0
        weighted = float(job.weight) * delta
        net = weighted - cost_equiv
        return VoIReport(
            p0=p0,
            p1=p1,
            delta_p=delta,
            weighted_gain=weighted,
            delay_s=delay,
            cost_s=float(ctx.review_cost_s),
            shadow_price=float(ctx.shadow_price),
            cost_equiv=cost_equiv,
            net_value=net,
            decided=bool(net > 0.0),
            basis="one more observation: gain w*(p1-p0) minus shadow_price*(delay+cost)",
        )