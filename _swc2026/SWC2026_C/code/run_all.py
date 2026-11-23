"""Run the whole P1/P2/P3 evidence chain. Entry point: python code/run_all.py.

Order matters: panel -> state -> P1 -> P2 (needs state) -> P3 (needs prefix_features).
Every step writes its own data/*.json; make_numbers rebuilds out/03-numbers.md from them.
"""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import os, subprocess, sys, time

PY = sys.executable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs")
os.makedirs(LOG, exist_ok=True)
STEPS = [
    ("panel", "build_panel.py"),
    ("p1_state", "p1_state.py"),
    ("p1_model", "p1_model.py"),
    ("p2_predict", "p2_predict.py"),
    ("p2_crossover", "p2_crossover.py"),
    ("p2_interval", "p2_interval.py"),
    ("p3_schedule", "p3_schedule.py"),
    ("numbers", "make_numbers.py"),
    ("verify", "verify_numbers.py"),
]

env = dict(os.environ, PYTHONIOENCODING="utf-8", OMP_NUM_THREADS="2", MPLBACKEND="Agg")
t0 = time.time()
for name, script in STEPS:
    t = time.time()
    log = os.path.join(LOG, name + ".log")
    print(f"[{name}] {script} ...", flush=True)
    with open(log, "w", encoding="utf-8") as fh:
        p = subprocess.run([PY, os.path.join(ROOT, "code", script)], cwd=ROOT,
                           stdout=fh, stderr=subprocess.STDOUT, env=env, text=True)
    dt = time.time() - t
    print(f"[{name}] exit={p.returncode} {dt:.1f}s log={log}", flush=True)
    if p.returncode != 0:
        print(open(log, encoding="utf-8").read()[-4000:])
        sys.exit(p.returncode)
print(f"ALL PASS in {time.time()-t0:.1f}s", flush=True)
