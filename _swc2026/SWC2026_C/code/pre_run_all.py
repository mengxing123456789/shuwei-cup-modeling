
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 全量下游跑批（增量落盘，可断点续跑）。

用法：
  python pre_run_all.py                 # 跑全部未完成的 run
  python pre_run_all.py --only C0       # 只跑某组对照
  python pre_run_all.py --Ls 30 --seeds 20261120

产物（不覆盖任何现有 data/*.json）：
  data/pre_p2_runs.jsonl     每个 run 一行（逐 run 追加，含完整 curve）
  data/pre_p2_results.json   同一批 run 的聚合视图（按 (arm,task,seed,L) 覆盖）
"""
import argparse
import json
import os
import time

from common import DATA
from pre_common import build_cache
from pre_downstream import probe_arm, train_arm

RUNS_JSONL = os.path.join(DATA, "pre_p2_runs.jsonl")
RES_JSON = os.path.join(DATA, "pre_p2_results.json")
LENS = [6, 18, 30, 60]
SEEDS = [20261120, 20261121, 20261122]


def key_of(r):
    return f"{r['arm']}|{r.get('ssl_task') or '-'}|{r['seed']}|{r['L']}"


def load_done():
    done = set()
    if os.path.exists(RUNS_JSONL):
        with open(RUNS_JSONL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(key_of(json.loads(line)))
                except Exception:
                    pass
    return done


def append_run(r):
    with open(RUNS_JSONL, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    agg = {"_meta": {"updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "note": "C0 从零 / C2 冻结探针 / C3 全量微调；C1 见 data/p2_gpu.json"},
           "runs": []}
    if os.path.exists(RES_JSON):
        with open(RES_JSON, encoding="utf-8") as f:
            old = json.load(f)
        agg["runs"] = [x for x in old.get("runs", [])
                       if key_of(x) != key_of(r)]
    agg["runs"].append({k: v for k, v in r.items() if k != "curve"})
    with open(RES_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="C0,C3A,C3B,C2A,C2B")
    ap.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    ap.add_argument("--Ls", default=",".join(map(str, LENS)))
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--redo", action="store_true",
                    help="重跑计划内的 run：先把这些 key 从 jsonl 里剔除再重算")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",") if x]
    Ls = [int(x) for x in a.Ls.split(",") if x]
    only = set(x.strip() for x in a.only.split(",") if x.strip())

    cache = build_cache()
    done = load_done()
    todo = []
    for L in Ls:
        for seed in seeds:
            if "C0" in only:
                todo.append(("C0", "A", seed, L))
            if "C3A" in only:
                todo.append(("C3", "A", seed, L))
            if "C3B" in only:
                todo.append(("C3", "B", seed, L))
            if "C2A" in only:
                todo.append(("C2", "A", seed, L))
            if "C2B" in only:
                todo.append(("C2", "B", seed, L))
    planned = todo
    todo = [t for t in planned
            if key_of(dict(arm=t[0], ssl_task=(t[1] if t[0] in ("C2", "C3") else None),
                           seed=t[2], L=t[3])) not in done]
    if a.redo and planned:
        todo = planned
        drop = {key_of(dict(arm=t[0], ssl_task=(t[1] if t[0] in ("C2", "C3") else None),
                            seed=t[2], L=t[3])) for t in planned}
        keep = []
        with open(RUNS_JSONL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if key_of(r) not in drop:
                    keep.append(line)
        with open(RUNS_JSONL, "w", encoding="utf-8", newline="\n") as f:
            for line in keep:
                f.write(line + "\n")
        print(f"[redo] dropped {len(drop)} old rows", flush=True)
    print(f"[plan] {len(todo)} runs to do, {len(done)} already done", flush=True)

    t0 = time.time()
    for i, (arm, task, seed, L) in enumerate(todo, 1):
        t1 = time.time()
        if arm == "C2":
            r = probe_arm(cache, task, seed, L)
        else:
            r = train_arm(cache, arm, task, seed, L, epochs=a.epochs)
        append_run(r)
        print(f"[{i}/{len(todo)}] {key_of(r)} rmse={r['rmse_cm']:.3f} "
              f"ep_rmse={r['endpoint_rmse_cm']:.3f} med={r['median_cm']:.3f} "
              f"q90={r['q90_cm']:.3f} best_ep={r['best_epoch']} "
              f"{time.time() - t1:.0f}s (总 {time.time() - t0:.0f}s)", flush=True)

    print(f"[done] {len(todo)} runs in {time.time() - t0:.0f}s -> {RES_JSON}", flush=True)


if __name__ == "__main__":
    main()