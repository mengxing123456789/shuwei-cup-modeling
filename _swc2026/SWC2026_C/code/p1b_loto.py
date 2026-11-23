# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P1-b leave-one-task-out (LOTO): how much of the unseen-task gap is task identity?

Reads (never writes) the existing artefacts:
    data/state.npz, data/panel_records.csv            -- features/labels/records
    ...\\Restocking_Tasks_and_Constraints\\source_segment_index.csv -- task per episode
Imports the model + recipe from code/train_gpu_p1b.py (test AUC 0.8220322044197129)
and re-runs it, unchanged, on training-split subsets.

Writes only NEW files:
    data/p1b_loto_prereg.json   -- decision rule, thresholds, class inventory (no AUC)
    data/p1b_loto.partial.json  -- checkpoint while folds are running
    data/p1b_loto.json          -- final result

Protocol
--------
* dominant task: record -> uuid -> most frequent `task` over that uuid's units.
* for each task class among the TRAIN records, hold its records out, train the same
  TCN with the same recipe/seed on the remaining train records, evaluate AUC/AP on
  the held-out train windows. Epoch selection stays on the untouched validation split.
* classes with < 2 records or < 20 positive windows are recorded as skipped.
* reference: one run over ALL train records, evaluated in-sample on the same
  per-class subsets, so "cost of leaving a task out" can be separated from
  "cost of the model being weak".

Run:  python code/p1b_loto.py --prereg      (once, before any training)
      python code/p1b_loto.py               (resumes from the checkpoint)
"""
import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import train_gpu_p1b as T  # noqa: E402  (reuse of the published recipe)

SEED = T.SEED
DATA = T.DATA
SRC_INDEX = (r"Restocking_Problem_and_Data_EN"
             r"\Restocking_Tasks_and_Constraints\source_segment_index.csv")
OUT = os.path.join(DATA, "p1b_loto.json")
PREREG = os.path.join(DATA, "p1b_loto_prereg.json")
PART = os.path.join(DATA, "p1b_loto.partial.json")

MIN_RECORDS = 2          # pre-registered skip thresholds
MIN_POSITIVES = 20
SENS_MIN_RECORDS = 1     # pre-registered exploratory relaxation
SENS_MIN_POSITIVES = 5
TEST_REF_AUC = 0.8220322044197129   # published unseen-task test AUC of train_gpu_p1b

RULE = ("claim: the LOTO gap is the fraction of the unseen-task gap explained by task identity; "
        "frac = (mean_auc_in_sample_reference - mean_auc_loto) / "
        "(mean_auc_in_sample_reference - 0.8220322044197129). "
        "Evaluated only if the denominator is positive (> 0); otherwise the fraction is "
        "recorded as null with reason 'denominator <= 0: in-sample reference is not above the "
        "published test AUC, so no optimism/gap can be apportioned'. "
        "mean_auc_in_sample_reference is matched to the LOTO evaluation sets: one model trained "
        "on all train records, then scored separately on each held-out class's windows, and "
        "averaged over exactly the classes used in mean_auc_loto. "
        "Pre-registered BEFORE any model in this script was trained.")


# ------------------------------------------------------------------ data (verbatim copy of T.build + record ids)
def build_with_rec():
    """Line-for-line copy of train_gpu_p1b.build(), plus the record id of every window."""
    z = np.load(os.path.join(DATA, "state.npz"))
    rec = z["rec"].astype(np.int64)
    feats = np.concatenate([
        z["fl"], z["fr"], z["gl"], z["gr"],
        z["validL"][:, None].astype(np.float32),
        z["validR"][:, None].astype(np.float32),
    ], axis=1).astype(np.float32)
    y = (z["badL"] | z["badR"]).astype(np.float32)

    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    split_of = dict(zip(meta["rec"].astype(int), meta["split"].astype(str)))
    env_of = dict(zip(meta["rec"].astype(int), meta["env"].astype(str)))

    bounds = {}
    for r in np.unique(rec):
        idx = np.flatnonzero(rec == r)
        bounds[int(r)] = (int(idx[0]), int(idx[-1]) + 1)

    X_parts, y_parts, s_parts, e_parts, r_parts = [], [], [], [], []
    for r, (lo, hi) in bounds.items():
        f = feats[lo:hi]
        lb = y[lo:hi]
        n = len(f)
        if n <= T.T:
            continue
        win = np.lib.stride_tricks.sliding_window_view(f, T.T, axis=0)
        win = np.transpose(win, (0, 2, 1))
        X_parts.append(np.ascontiguousarray(win, dtype=np.float32))
        y_parts.append(lb[T.T - 1:])
        s_parts.append(np.array([split_of[r]] * len(y_parts[-1])))
        e_parts.append(np.array([env_of[r]] * len(y_parts[-1])))
        r_parts.append(np.full(len(y_parts[-1]), r, dtype=np.int64))

    X = np.concatenate(X_parts, axis=0)
    Y = np.concatenate(y_parts, axis=0)
    S = np.concatenate(s_parts, axis=0)
    E = np.concatenate(e_parts, axis=0)
    R = np.concatenate(r_parts, axis=0)
    del X_parts, y_parts, s_parts, e_parts, r_parts
    return X, Y, S, E, R


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_mapping():
    """record id -> dominant task, via uuid -> source_segment_index.task (most frequent)."""
    meta = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    idx = pd.read_csv(SRC_INDEX)

    tasks = defaultdict(Counter)
    for u, t in zip(idx["episode_uuid"].astype(str), idx["task"].astype(str)):
        tasks[u][str(t)] += 1

    uuid_of = dict(zip(meta["rec"].astype(int), meta["uuid"].astype(str)))
    split_of = dict(zip(meta["rec"].astype(int), meta["split"].astype(str)))
    env_of = dict(zip(meta["rec"].astype(int), meta["env"].astype(str)))

    dom, dropped, ties, units_used = {}, [], [], {}
    for r in sorted(uuid_of):
        u = uuid_of[r]
        cand = tasks.get(u)
        if not cand:
            dropped.append(int(r))
            continue
        top = max(cand.values())
        winners = [k for k, v in cand.items() if v == top]
        if len(winners) > 1:
            ties.append(int(r))
        dom[int(r)] = cand.most_common(1)[0][0]
        units_used[int(r)] = int(top)

    return dom, split_of, env_of, dropped, ties, units_used, len(idx), len(meta)


def window_table(Y, R):
    """windows / positives per record, exactly as build_with_rec lays them out."""
    win, pos = {}, {}
    for r in np.unique(R):
        m = R == r
        win[int(r)] = int(m.sum())
        pos[int(r)] = int(Y[m].sum())
    return win, pos


# ------------------------------------------------------------------ training (same recipe as T.main)
def predict(model, Xnp, bs=8192):
    model.eval()
    outs = []
    with torch.no_grad():
        for i in range(0, len(Xnp), bs):
            xb = torch.from_numpy(np.ascontiguousarray(Xnp[i:i + bs])).to(T.DEV, non_blocking=True)
            outs.append(torch.sigmoid(model(xb)).cpu().numpy())
    if not outs:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(outs)


def train_once(X, Y, idx_tr, idx_va, idx_ev):
    """Train the published TCN on idx_tr, select epoch on idx_va, score idx_ev."""
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    Xtr = torch.from_numpy(np.ascontiguousarray(X[idx_tr]))
    ytr = torch.from_numpy(np.ascontiguousarray(Y[idx_tr]))
    Xva_np = np.ascontiguousarray(X[idx_va])
    yva = Y[idx_va]

    pos = float(ytr.sum())
    neg = float(len(ytr) - pos)
    pw = torch.tensor([neg / max(pos, 1.0)], device=T.DEV)

    model = T.TCN(X.shape[2]).to(T.DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=T.LR, weight_decay=T.WD)
    steps = (len(Xtr) + T.BATCH - 1) // T.BATCH
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=T.LR, total_steps=T.EPOCHS * steps)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)

    best = {"auc": -1.0, "epoch": -1, "state": None}
    for ep in range(1, T.EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(Xtr))
        tot, nseen = 0.0, 0
        for i in range(steps):
            sel = perm[i * T.BATCH:(i + 1) * T.BATCH]
            xb = Xtr[sel].to(T.DEV, non_blocking=True)
            yb = ytr[sel].to(T.DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            out = model(xb)
            loss = lossf(out, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            sched.step()
            tot += float(loss) * len(sel)
            nseen += len(sel)
        pv = predict(model, Xva_np)
        auc = roc_auc_score(yva, pv)
        if auc > best["auc"]:
            best = {"auc": float(auc), "epoch": ep,
                    "state": {k: v.detach().clone() for k, v in model.state_dict().items()}}

    model.load_state_dict(best["state"])
    model.eval()
    pred = predict(model, np.ascontiguousarray(X[idx_ev]))
    del Xtr, ytr, model
    torch.cuda.empty_cache()
    return best, pred


# ------------------------------------------------------------------ protocol
def class_inventory(dom, split_of, win, pos):
    tr_recs = [r for r in sorted(dom) if split_of.get(r) == "train"]
    by_class = defaultdict(list)
    for r in tr_recs:
        by_class[dom[r]].append(r)
    inv = []
    for t in sorted(by_class):
        rr = by_class[t]
        inv.append({
            "task": t,
            "n_records": len(rr),
            "n_windows": int(sum(win[r] for r in rr)),
            "positives": int(sum(pos[r] for r in rr)),
            "records": rr,
        })
    return inv, by_class, tr_recs


def skip_reason(row, min_rec, min_pos):
    rs = []
    if row["n_records"] < min_rec:
        rs.append(f"n_records={row['n_records']} < {min_rec}")
    if row["positives"] < min_pos:
        rs.append(f"positives={row['positives']} < {min_pos}")
    return "; ".join(rs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", action="store_true", help="write the pre-registration only")
    ap.add_argument("--budget", type=float, default=480.0, help="soft wall-clock budget (s)")
    ap.add_argument("--max-folds", type=int, default=0, help="stop after N folds (0 = no cap)")
    ap.add_argument("--fresh", action="store_true", help="ignore an existing checkpoint")
    args = ap.parse_args()

    t0 = time.time()
    dom, split_of, env_of, dropped, ties, units_used, n_units, n_recs = load_mapping()
    z = np.load(os.path.join(DATA, "state.npz"))
    Rz = z["rec"].astype(np.int64)
    Yz = (z["badL"] | z["badR"]).astype(np.float32)
    win, pos = {}, {}
    for r in np.unique(Rz):
        k = int((Rz == r).sum())
        win[int(r)] = max(0, k - (T.T - 1))
        pos[int(r)] = int(Yz[Rz == r][T.T - 1:].sum()) if win[int(r)] > 0 else 0
    del z, Rz, Yz

    inv, by_class, tr_recs = class_inventory(dom, split_of, win, pos)
    n_dom_tr = len(tr_recs)

    primary, skipped_primary = [], []
    for row in inv:
        if row["n_records"] >= MIN_RECORDS and row["positives"] >= MIN_POSITIVES:
            primary.append(row)
        else:
            skipped_primary.append(dict(row, reason=skip_reason(row, MIN_RECORDS, MIN_POSITIVES)))
    sens_extra = [dict(row, reason=skip_reason(row, SENS_MIN_RECORDS, SENS_MIN_POSITIVES))
                  for row in inv
                  if row["task"] not in {p["task"] for p in primary}
                  and row["n_records"] >= SENS_MIN_RECORDS
                  and row["positives"] >= SENS_MIN_POSITIVES]

    hashes = {
        "data/state.npz": sha256(os.path.join(DATA, "state.npz")),
        "data/panel_records.csv": sha256(os.path.join(DATA, "panel_records.csv")),
        "source_segment_index.csv": sha256(SRC_INDEX),
    }

    # ---------------------------------------------------------------- pre-registration
    if args.prereg:
        prereg = {
            "_meta": {
                "script": "code/p1b_loto.py",
                "written_local": time.strftime("%Y-%m-%d %H:%M:%S"),
                "purpose": "measure, inside the TRAIN split, how much of the unseen-task test gap "
                           "is attributable to task identity (leave-one-task-out).",
                "decision_rule_preregistered": RULE,
                "thresholds": {"primary": {"min_records": MIN_RECORDS, "min_positives": MIN_POSITIVES},
                               "exploratory_relaxation": {"min_records": SENS_MIN_RECORDS,
                                                          "min_positives": SENS_MIN_POSITIVES}},
                "epoch_selection": "best validation AUC on the untouched official validation split "
                                   "(7 records / 4 envs); the held-out task class is never scored "
                                   "during training and never used for any choice.",
                "recipe": {
                    "imported_from": "code/train_gpu_p1b.py (T.TCN, T.T, T.BATCH, T.EPOCHS, T.LR, T.WD, T.SEED)",
                    "window_frames": T.T, "batch": T.BATCH, "epochs": T.EPOCHS,
                    "lr": T.LR, "weight_decay": T.WD, "seed": SEED,
                    "note": "same model class, same optimiser schedule, same seed; build() copied "
                            "line-for-line with a per-window record-id output.",
                },
                "confound_note": ("Every class that survives the thresholds maps to its own "
                                  "environment(s): at record granularity LOTO cannot be separated "
                                  "from leave-one-environment-out for these classes. Recorded "
                                  "before any AUC was computed; see per-class env fields."),
                "input_sha256": hashes,
                "task_assignment": "record -> uuid (panel_records.csv) -> most frequent task over "
                                   "that uuid's units in source_segment_index.csv",
                "records_without_unit": dropped,
                "records_with_tied_dominant_task": ties,
                "counts": {"panel_records": n_recs, "source_segment_units": n_units,
                           "train_records_with_dominant_task": n_dom_tr,
                           "train_classes": len(inv),
                           "primary_classes": len(primary),
                           "skipped_classes": len(skipped_primary),
                           "exploratory_extra_classes": len(sens_extra)},
                "primary_class_inventory": [{k: row[k] for k in
                                             ("task", "n_records", "n_windows", "positives")}
                                            for row in primary],
                "skipped_class_inventory": [{k: row[k] for k in
                                             ("task", "n_records", "n_windows", "positives", "reason")}
                                            for row in skipped_primary],
                "exploratory_extra_inventory": [{k: row[k] for k in
                                                 ("task", "n_records", "n_windows", "positives",
                                                  "reason")} for row in sens_extra],
                "no_auc_has_been_computed_yet": True,
            }
        }
        with open(PREREG, "w", encoding="utf-8", newline="\n") as f:
            json.dump(prereg, f, ensure_ascii=False, indent=1)
        print(f"pre-registration -> {PREREG}")
        print(f"train classes={len(inv)}  primary={len(primary)}  skipped={len(skipped_primary)}  "
              f"exploratory_extra={len(sens_extra)}")
        return

    # ---------------------------------------------------------------- build + parity
    partial = {"folds": {}, "reference": None, "build_parity": None, "t0_local": None}
    if os.path.exists(PART) and not args.fresh:
        with open(PART, encoding="utf-8") as f:
            partial = json.load(f)
        print(f"resuming checkpoint: {len(partial['folds'])} folds done, "
              f"reference={'yes' if partial.get('reference') else 'no'}")
    partial["t0_local"] = partial.get("t0_local") or time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"loading panel ...")
    X, Y, S, E, R = build_with_rec()
    print(f"windows={len(X):,}  feat={X.shape[2]}  T={T.T}  pos_rate={Y.mean():.5f}")
    print(f"split  train={(S == 'train').sum():,}  val={(S == 'validation').sum():,}  "
          f"test={(S == 'test').sum():,}")

    if partial.get("build_parity") is None:
        tp = time.time()
        Xo, Yo, So, Eo = T.build()
        parity = {
            "same_shape": list(X.shape) == list(Xo.shape),
            "X_equal": bool(np.array_equal(X, Xo)),
            "Y_equal": bool(np.array_equal(Y, Yo)),
            "S_equal": bool(np.array_equal(S, So)),
            "E_equal": bool(np.array_equal(E, Eo)),
            "seconds": round(time.time() - tp, 1),
        }
        del Xo, Yo, So, Eo
        if not (parity["same_shape"] and parity["X_equal"] and parity["Y_equal"]
                and parity["S_equal"] and parity["E_equal"]):
            raise SystemExit(f"build parity FAILED: {parity}")
        partial["build_parity"] = parity
        print(f"build parity OK ({parity['seconds']}s): copy == train_gpu_p1b.build()")

    # window index per record
    widx = {}
    for r in np.unique(R):
        widx[int(r)] = np.flatnonzero(R == r)
    idx_va = np.concatenate([widx[r] for r in sorted(split_of) if split_of[r] == "validation"])
    idx_all_tr = np.concatenate([widx[r] for r in tr_recs])

    print(f"train windows={len(idx_all_tr):,}  app_pos={int(Y[idx_all_tr].sum()):,}  "
          f"val windows={len(idx_va):,}")

    def budget_hit():
        return (time.time() - t0) > args.budget

    # ---------------------------------------------------------------- folds
    queue = [(row, "primary") for row in primary] + [(row, "exploratory") for row in sens_extra]
    done_now = 0
    for row, tier in queue:
        task = row["task"]
        if task in partial["folds"]:
            continue
        if budget_hit() or (args.max_folds and done_now >= args.max_folds):
            print(f"-- budget/max-folds reached, stopping before '{task}' (resume later)")
            break
        tf = time.time()
        idx_ev = np.concatenate([widx[r] for r in row["records"]])
        idx_tr = np.concatenate([widx[r] for r in tr_recs if dom[r] != task])
        hold_envs = sorted({env_of[r] for r in row["records"]})
        sub_envs = {env_of[r] for r in tr_recs if dom[r] != task}
        entry = {k: row[k] for k in ("task", "n_records", "n_windows", "positives")}
        entry.update({
            "tier": tier, "skipped": False, "reason": None,
            "auc": None, "ap": None,
            "train_windows": int(len(idx_tr)), "train_positives": int(Y[idx_tr].sum()),
            "n_envs_heldout": len(hold_envs), "envs_heldout": hold_envs,
            "envs_shared_with_training_subset": sorted(set(hold_envs) & sub_envs),
        })
        try:
            best, pred = train_once(X, Y, idx_tr, idx_va, idx_ev)
            yev = Y[idx_ev]
            entry["auc"] = float(roc_auc_score(yev, pred))
            entry["ap"] = float(average_precision_score(yev, pred))
            entry["best_epoch"] = int(best["epoch"])
            entry["val_auc_at_best"] = float(best["auc"])
        except Exception as exc:                                # noqa: BLE001
            entry["skipped"] = True
            entry["reason"] = f"exception: {type(exc).__name__}: {exc}"
            traceback.print_exc()
        entry["seconds"] = round(time.time() - tf, 1)
        partial["folds"][task] = entry
        done_now += 1
        with open(PART, "w", encoding="utf-8", newline="\n") as f:
            json.dump(partial, f, ensure_ascii=False, indent=1)
        print(f"[{tier[:4]}] {task[:52]:52s} recs={row['n_records']:2d} "
              f"win={row['n_windows']:5d} pos={row['positives']:4d} "
              f"auc={entry['auc'] if entry['auc'] is None else round(entry['auc'], 4)} "
              f"ep={entry.get('best_epoch', '-')} {entry['seconds']}s")

    # ---------------------------------------------------------------- in-sample reference
    used_rows = [row for row in primary if partial["folds"].get(row["task"], {}).get("auc") is not None]
    if partial.get("reference") is None and len(used_rows) > 0:
        if budget_hit():
            print("-- budget reached before the in-sample reference; resume later")
            with open(PART, "w", encoding="utf-8", newline="\n") as f:
                json.dump(partial, f, ensure_ascii=False, indent=1)
            return
        tf = time.time()
        print("reference: one run on ALL train records, in-sample")
        best, pred = train_once(X, Y, idx_all_tr, idx_va, idx_all_tr)
        ytr_all = Y[idx_all_tr]
        ref = {
            "auc_all_train_windows": float(roc_auc_score(ytr_all, pred)),
            "ap_all_train_windows": float(average_precision_score(ytr_all, pred)),
            "best_epoch": int(best["epoch"]),
            "val_auc_at_best": float(best["auc"]),
            "per_class": {},
            "seconds": round(time.time() - tf, 1),
        }
        for row in primary + sens_extra:
            m = np.isin(R[idx_all_tr], row["records"])
            yy = ytr_all[m]
            pp = pred[m]
            if yy.sum() == 0 or (yy == 0).all():
                continue
            ref["per_class"][row["task"]] = {
                "n_windows": int(m.sum()), "positives": int(yy.sum()),
                "auc": float(roc_auc_score(yy, pp)),
                "ap": float(average_precision_score(yy, pp)),
            }
        ref["parity_with_published_p1b_gpu"] = {
            "published_val_auc_at_best": 0.8852539948743638,
            "val_auc_at_best_equal": bool(abs(ref["val_auc_at_best"] - 0.8852539948743638) < 1e-12),
            "published_best_epoch": 1,
            "best_epoch_equal": bool(ref["best_epoch"] == 1),
        }
        ref["seconds"] = round(time.time() - tf, 1)
        partial["reference"] = ref
        with open(PART, "w", encoding="utf-8", newline="\n") as f:
            json.dump(partial, f, ensure_ascii=False, indent=1)
        print(f"reference auc(all train)={ref['auc_all_train_windows']:.4f}  "
              f"ep={ref['best_epoch']}  val={ref['val_auc_at_best']:.6f}  {ref['seconds']}s")

    # ---------------------------------------------------------------- final assembly
    folds = partial["folds"]
    missing = [row["task"] for row, _ in queue if row["task"] not in folds]
    if missing or partial.get("reference") is None:
        print(f"INCOMPLETE: {len(missing)} folds missing, reference="
              f"{'yes' if partial.get('reference') else 'no'} -- rerun the same command")
        return

    per_class = []
    for row in inv:
        task = row["task"]
        if task in folds:
            per_class.append(folds[task])
        else:
            per_class.append({
                "task": task, "n_records": row["n_records"], "n_windows": row["n_windows"],
                "positives": row["positives"], "auc": None, "ap": None,
                "skipped": True,
                "reason": skip_reason(row, MIN_RECORDS, MIN_POSITIVES),
                "tier": "excluded",
            })

    used = [r for r in per_class if r.get("tier") == "primary" and not r.get("skipped")
            and r.get("auc") is not None]
    ref = partial["reference"]
    ref_pc = ref["per_class"]
    matched = [ref_pc[r["task"]]["auc"] for r in used if r["task"] in ref_pc]
    mean_loto = float(np.mean([r["auc"] for r in used])) if used else None
    mean_ref = float(np.mean(matched)) if matched else None
    gap = (mean_ref - mean_loto) if (mean_ref is not None and mean_loto is not None) else None

    denom = (mean_ref - TEST_REF_AUC) if mean_ref is not None else None
    if denom is not None and denom > 0 and gap is not None:
        frac = float(gap / denom)
        frac_ok = True
        frac_reason = None
    else:
        frac = None
        frac_ok = False
        frac_reason = ("denominator <= 0: in-sample reference is not above the published test AUC, "
                       "so no optimism/gap can be apportioned")

    sens_used = [r for r in per_class if r.get("tier") == "exploratory" and not r.get("skipped")
                 and r.get("auc") is not None]
    sens_mean = float(np.mean([r["auc"] for r in sens_used])) if sens_used else None
    sens_matched = [ref_pc[r["task"]]["auc"] for r in sens_used if r["task"] in ref_pc]
    sens_ref_mean = float(np.mean(sens_matched)) if sens_matched else None

    res = {
        "_meta": {
            "script": "code/p1b_loto.py",
            "created_local": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seed": SEED,
            "epochs": T.EPOCHS,
            "budget_seconds_per_invocation": args.budget,
            "epoch_selection": "best validation AUC on the untouched official validation split "
                               "(7 records / 4 envs); the held-out task class is never scored during "
                               "training and never used for any choice.",
            "recipe": "code/train_gpu_p1b.py imported as T, not modified: TCN (4 residual blocks, "
                      "dilations 1/2/4/8, 96 channels, GroupNorm(8), GELU, dropout 0.10, head "
                      "Linear(192->64)->GELU->Linear(64->1)); 82-dim per-frame features "
                      "(fl32+fr32+gl8+gr8+validL+validR); causal 15-frame window @30 fps; "
                      "BCEWithLogits with pos_weight=neg/pos; AdamW lr 2e-3 wd 1e-4; OneCycleLR; "
                      "batch 1024; grad clip 2.0; 18 epochs; torch.manual_seed/np.random.seed(SEED) "
                      "at the start of every fold. No git in this repo; build() was copied "
                      "line-for-line and verified equal to T.build() (see build_parity).",
            "window_frames": T.T, "batch": T.BATCH, "lr": T.LR, "weight_decay": T.WD,
            "device": T.DEV, "torch": torch.__version__,
            "split_used": "panel_records.csv split column: train 55 records / 16 envs, validation "
                          "7 / 4, test 7 / 4. Folds and reference are built from TRAIN records only; "
                          "validation is used only for epoch selection; test is never touched.",
            "task_assignment": "record -> uuid (panel_records.csv 'uuid') -> most frequent 'task' "
                               "over that uuid's units in source_segment_index.csv",
            "records_without_unit": dropped,
            "records_dropped_from_loto": len(dropped),
            "records_with_tied_dominant_task": ties,
            "counts": {"panel_records": n_recs, "source_segment_units": n_units,
                       "train_records_with_dominant_task": n_dom_tr,
                       "train_classes": len(inv),
                       "primary_classes_used": len(used),
                       "primary_classes_skipped": len(skipped_primary),
                       "exploratory_extra_classes": len(sens_used)},
            "thresholds": {"min_records": MIN_RECORDS, "min_positives": MIN_POSITIVES,
                           "exploratory_min_records": SENS_MIN_RECORDS,
                           "exploratory_min_positives": SENS_MIN_POSITIVES},
            "decision_rule_preregistered": RULE,
            "decision_rule_file": "data/p1b_loto_prereg.json (written before any training)",
            "confound_note": ("Every usable class maps to its own environment(s): at record "
                              "granularity a task fold is also an environment fold for these "
                              "classes (see n_envs_heldout / envs_shared_with_training_subset per "
                              "class). The measured LOTO gap therefore bounds task + environment "
                              "jointly, not task identity alone."),
            "build_parity": partial["build_parity"],
            "reference_parity": ref.get("parity_with_published_p1b_gpu"),
            "input_sha256": hashes,
            "summary_of_protocol": "same model, same seed, only the training-record set changes.",
        },
        "per_class": per_class,
        "in_sample_reference": {
            "what": "one model trained on all train records, then scored in-sample",
            "auc_all_train_windows": ref["auc_all_train_windows"],
            "ap_all_train_windows": ref["ap_all_train_windows"],
            "best_epoch": ref["best_epoch"],
            "val_auc_at_best": ref["val_auc_at_best"],
            "per_class_matched_to_loto_eval_sets": ref_pc,
            "seconds": ref["seconds"],
        },
        "sensitivity_relaxed_thresholds": {
            "rule": f"exploratory only, not the pre-registered claim: min_records={SENS_MIN_RECORDS}, "
                    f"min_positives={SENS_MIN_POSITIVES}",
            "per_class": [r for r in per_class if r.get("tier") == "exploratory"],
            "n_classes_used": len(sens_used),
            "mean_auc_loto_exploratory": sens_mean,
            "mean_auc_in_sample_reference_matched": sens_ref_mean,
            "gap_exploratory": (sens_ref_mean - sens_mean)
                               if (sens_ref_mean is not None and sens_mean is not None) else None,
        },
        "summary": {
            "n_classes_used": len(used),
            "n_classes_skipped": len(skipped_primary),
            "n_classes_below_primary_thresholds": len(skipped_primary),
            "n_classes_exploratory_only": len(sens_used),
            "n_classes_skipped_without_any_result": sum(
                1 for r in per_class if r.get("skipped") and r.get("auc") is None),
            "n_train_classes": len(inv),
            "mean_auc_loto": mean_loto,
            "mean_auc_in_sample_reference": mean_ref,
            "gap_mean": gap,
            "mean_auc_test_reference": TEST_REF_AUC,
            "gap_definition": "mean_auc_in_sample_reference - mean_auc_loto",
            "frac_unseen_task_gap_explained": frac,
            "frac_interpretable": frac_ok,
            "frac_reason": frac_reason,
            "rule_denominator": denom,
            "wall_seconds_this_invocation": round(time.time() - t0, 1),
        },
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # ---------------------------------------------------------------- compact table
    print("\n=== LOTO (train split) ===")
    print(f"{'task':44s} {'recs':>4s} {'win':>6s} {'pos':>5s} {'auc':>7s} {'ap':>7s}  note")
    for r in per_class:
        auc = "-" if r["auc"] is None else f"{r['auc']:.4f}"
        app = "-" if r.get("ap") is None else f"{r['ap']:.4f}"
        note = "skipped: " + r["reason"] if r.get("skipped") and r.get("tier") == "excluded" else \
            ("SKIP " + str(r.get("reason")) if r.get("skipped") else "")
        print(f"{r['task'][:44]:44s} {r['n_records']:4d} {r['n_windows']:6d} {r['positives']:5d} "
              f"{auc:>7s} {app:>7s}  {note}")
    print()
    print(f"SUMMARY  classes_used={len(used)}  below_primary_thresholds={len(skipped_primary)}  "
          f"(of which exploratory_only={len(sens_used)})  "
          f"mean_auc_loto={mean_loto:.4f}  "
          f"mean_auc_in_sample_reference={mean_ref:.4f}  gap={gap:+.4f}  "
          f"test_ref={TEST_REF_AUC:.4f}  frac_explained="
          f"{'null' if frac is None else f'{frac:+.3f}'}")
    if sens_used:
        print(f"EXPLORATORY (relaxed)  classes={len(sens_used)}  "
              f"mean_auc_loto={sens_mean:.4f}  mean_ref={sens_ref_mean:.4f}")
    print(f"\nsaved -> {OUT}   ({time.time() - t0:.1f}s this invocation)")
    os.remove(PART)


if __name__ == "__main__":
    main()