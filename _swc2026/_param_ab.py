# -*- coding: utf-8 -*-
"""Parameterize alt_p3_ccmip.py for the official 5 service-duration mappings
p = alpha*d + beta.  All new params default to the nominal (1.0, 0.5) so every
existing caller (alt_p3.json generation, alt_p3_sweep.py) is byte-identical.

The transformation mirrors the vendored official engine's
    scenarios(): alpha * max(prefix, pred + residual) + beta
    realized:    p = alpha * d + beta
Both the MIP's scenario durations AND the realized duration must move together,
otherwise we would be testing a world where the plan and reality disagree.
"""
import pathlib

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\code\alt_p3_ccmip.py")
t = P.read_text(encoding="utf-8")
orig = t
REPL = []

# 1) scenario_durations signature + return
REPL.append((
    "def scenario_durations(job, level: int, qbank, n_scen: int, idx=None):\n"
    '    """Duration scenarios (alpha*d+beta, alpha=1, beta=.5) at observation level.',
    "def scenario_durations(job, level: int, qbank, n_scen: int, idx=None,\n"
    "                       alpha: float = 1.0, beta: float = 0.5):\n"
    '    """Duration scenarios (alpha*d+beta) at observation level.\n'
    "    ``alpha``/``beta`` are the official service-duration mapping; the nominal\n"
    "    (1.0, 0.5) reproduces the original scenario set exactly."
))
REPL.append((
    "    return [max(p, pred + float(r)) + 0.5 for r in q]",
    "    return [alpha * max(p, pred + float(r)) + beta for r in q]"
))

# 2) reserve_for: thread alpha/beta to scenario_durations
REPL.append((
    "def reserve_for(job, level: int, qbank, eps: float, n_scen: int):\n"
    '    """Chance-constrained reserve: smallest b with P(p_j > b) <= eps."""\n'
    "    vals = sorted(scenario_durations(job, level, qbank, n_scen))",
    "def reserve_for(job, level: int, qbank, eps: float, n_scen: int,\n"
    "                alpha: float = 1.0, beta: float = 0.5):\n"
    '    """Chance-constrained reserve: smallest b with P(p_j > b) <= eps."""\n'
    "    vals = sorted(scenario_durations(job, level, qbank, n_scen,\n"
    "                                    alpha=alpha, beta=beta))"
))

# 3) solve_plan signature
REPL.append((
    "def solve_plan(jobs, t0, zone0, H, B_rem, K_rem, qbank, n_scen,\n"
    "               eps=0.5, lam=0.01, time_limit=3.0, workers=8,\n"
    "               max_jobs=None, b_cap_mult=1.6):",
    "def solve_plan(jobs, t0, zone0, H, B_rem, K_rem, qbank, n_scen,\n"
    "               eps=0.5, lam=0.01, time_limit=3.0, workers=8,\n"
    "               max_jobs=None, b_cap_mult=1.6,\n"
    "               alpha=1.0, beta=0.5):"
))
# 3b) solve_plan's scenario_durations call
REPL.append((
    "            cand[l] = [int(round(v * 10))\n"
    "                       for v in scenario_durations(j, l, qbank, n_scen, idx=sidx)]",
    "            cand[l] = [int(round(v * 10))\n"
    "                       for v in scenario_durations(j, l, qbank, n_scen, idx=sidx,\n"
    "                                                   alpha=alpha, beta=beta)]"
))

# 4) run_episode signature + remove hardcoded alpha/beta + thread to solve_plan & reserve_for
REPL.append((
    "def run_episode(case, seed, policy, qbank, n_scen, eps, lam, time_limit, workers):",
    "def run_episode(case, seed, policy, qbank, n_scen, eps, lam, time_limit, workers,\n"
    "                alpha=1.0, beta=0.5):"
))
REPL.append((
    "    K = int(conf[\"observation_limit\"])\n"
    "    alpha, beta = 1.0, 0.5\n",
    "    K = int(conf[\"observation_limit\"])\n"
))
REPL.append((
    "                plan = solve_plan(active, t, zone, H, B - cost, K - nreview, qb, ns,\n"
    "                                  eps=(1.0 if not joint else eps),\n"
    "                                  lam=lam, time_limit=time_limit, workers=workers)",
    "                plan = solve_plan(active, t, zone, H, B - cost, K - nreview, qb, ns,\n"
    "                                  eps=(1.0 if not joint else eps),\n"
    "                                  lam=lam, time_limit=time_limit, workers=workers,\n"
    "                                  alpha=alpha, beta=beta)"
))
REPL.append((
    "            b = reserve_for(target, target[\"level\"], qbank, eps, n_scen)",
    "            b = reserve_for(target, target[\"level\"], qbank, eps, n_scen,\n"
    "                           alpha=alpha, beta=beta)"
))

# 5) run_baseline: forward mapping to official simulate()
REPL.append((
    "def run_baseline(mod, case, seed, policy):\n"
    "    r = mod.simulate(case, seed, policy)",
    "def run_baseline(mod, case, seed, policy, alpha=1.0, beta=0.5):\n"
    "    r = mod.simulate(case, seed, policy, alpha, beta)"
))

for old, new in REPL:
    n = t.count(old)
    assert n == 1, "count=%d for:\n%s" % (n, old[:120])
    t = t.replace(old, new, 1)

assert t != orig
P.write_bytes(t.encode("utf-8"))
print("PARAM OK  %d edits, %d bytes" % (len(REPL), len(t.encode("utf-8"))))
