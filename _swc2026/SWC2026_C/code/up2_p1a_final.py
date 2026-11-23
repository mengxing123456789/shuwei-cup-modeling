# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P1-a v2 final evaluation -- TEST IS EVALUATED ONCE, with rules frozen on validation.

Reads data/up2_p1a_val2.json (produced by up2_p1a_select.py, validation only), decodes
the test records with those frozen rules and writes data/up2_p1a.json:

    {baseline, configs[{name,params,val_ari,val_bf1,test_ari,test_bf1,
                        k_err,per_env,seconds,params_count}],
     best, gate{...}, passes, notes}

Pre-registered gate (written before any training, see up2_p1a_lib.py docstring):
    test mean ARI >= 0.62  AND  test mean boundary F1 >= 0.30
`passes` is the conjunction; it is reported honestly even when false.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import up2_p1a_lib as L
import up2_p1a_train as T

GATE = dict(test_ari=0.62, test_bf1=0.30)


def mix(sig, chg, w):
    if chg is None or w == 0:
        return sig
    return L.zscore(sig) + w * L.zscore(chg)


def load_val():
    p = os.path.join(L.DATA, "up2_p1a_val2.json")
    if not os.path.exists(p):
        raise SystemExit("run up2_p1a_select.py first (no frozen rules)")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sig_of(s, rule):
    """Decoder input for one frozen rule: 'chg' family or a z-space mix."""
    if rule["sig"] == "chg":
        return L.zscore(s["chg"])
    return mix(s["score"], s["chg"], rule["w"])


def test_scores(src, D, Xf):
    """Return {rec: {score, chg}} for the TEST records of one source."""
    TE = L.ids(D, "test")
    if src == "ens":
        parts = {k: test_scores(k, D, Xf) for k in ("v1", "mtask", "sslmtask")}
        out = {}
        for r in TE:
            sc = [L.zscore(parts[k][r]["score"]) for k in parts]
            ch = [L.zscore(parts[k][r]["chg"]) for k in parts if parts[k][r]["chg"] is not None]
            out[r] = dict(score=np.mean(sc, 0), chg=(np.mean(ch, 0) if ch else None))
        return out
    if src == "v1":
        z = np.load(os.path.join(L.DATA, "up_p1a_scores.npz"), allow_pickle=True)
        rec = [int(r) for r in z["rec"]]
        return {r: dict(score=z["score"][rec.index(r)].astype(np.float64), chg=None)
                for r in TE}
    tag = src
    meta_p = os.path.join(L.DATA, f"up2_p1a_train_{tag}.json")
    with open(meta_p, encoding="utf-8") as f:
        meta = json.load(f)
    ckpts = [os.path.join(L.MODELS, f"up2_p1a_{tag}_seed{s}.pt") for s in meta["seeds"]]
    sc, ch = {}, {}
    for c in ckpts:
        if not os.path.exists(c):
            raise SystemExit(f"missing checkpoint {c}")
        net = T.MultiTask(Xf[0].shape[1])
        net.load_state_dict(torch.load(c, map_location=T.DEVICE))
        net.to(T.DEVICE)
        out = T.infer_scores(net, Xf, TE, D)
        for r in TE:
            sc.setdefault(r, []).append(out[r]["score"].astype(np.float64))
            ch.setdefault(r, []).append(out[r]["chg"].astype(np.float64))
    return {r: dict(score=np.mean(sc[r], 0), chg=np.mean(ch[r], 0)) for r in TE}


def decode(pred, rule, D, recs, prior=None):
    """Replay one frozen rule; the K prior is only used when its penalty is non-zero."""
    khat = {}
    if rule.get("k_pen", 0.0) > 0:
        model = (prior or {})[rule["src"]]
        model = (np.array(model["mu"]), np.array(model["sd"]),
                 np.array(model["coef"]), model["b"])
        for r in recs:
            i = L.pos(D, r)
            x = L.k_features(pred[r]["score"], D["dur"][i], D["n"][i], D["bad"][i])
            khat[r] = max(1, int(round(L.predict_k(model, x))))
    return {r: L.decode_dp(sig_of(pred[r], rule),
                           sigma=rule["sigma"], min_len=rule["min_len"],
                           lam=rule["lam"], cand_dist=5, prom_floor=0.02,
                           shift=rule["shift"], k_hat=khat.get(r),
                           k_pen=rule.get("k_pen", 0.0), n=D["n"][L.pos(D, r)])
            for r in recs}


def count_params(paths):
    n = 0
    for p in paths:
        if not os.path.exists(p):
            return None
        sd = torch.load(p, map_location="cpu")
        for v in (sd.values() if isinstance(sd, dict) else []):
            if hasattr(v, "numel"):
                n += int(v.numel())
    return n


def params_of(src):
    """Total parameters of the networks actually used to score test (all seeds)."""
    v1 = count_params(sorted(glob.glob(os.path.join(L.MODELS, "p1a_seg_seed*.pt"))))
    def one(tag):
        mp = os.path.join(L.DATA, f"up2_p1a_train_{tag}.json")
        if not os.path.exists(mp):
            return None
        with open(mp, encoding="utf-8") as f:
            m = json.load(f)
        return int(m["params"]) * len(m["seeds"])
    nn = [one("mtask"), one("sslmtask")]
    if src == "v1":
        return v1
    if src == "mtask":
        return nn[0]
    if src == "sslmtask":
        return nn[1]
    vals = [v for v in [v1] + nn if v]
    return int(sum(vals)) if vals else None


def main():
    t0 = time.time()
    D, Xf = T.load_features()
    val = load_val()
    TE = L.ids(D, "test")

    base = L.load_json(os.path.join(L.DATA, "up_p1a_final.json"))
    baseline = dict(name=f"v1 published-best rule ({base['summary']['best_rule_on_test']})",
                    test_ari=float(base["summary"]["test_mean_ari"]),
                    test_bf1=float(base["summary"]["mean_boundary_f1"]),
                    published_ari=float(base["_meta"]["published_baseline_ari"]),
                    note="已经在论文中发表的口径；由 up_p1a_probe_scores.py 精确复现（abs_diff 0.0）")

    cfg = []
    best_rule = None
    for src in ("v1", "mtask", "sslmtask", "ens"):
        rule = val["frozen"].get(src)
        if rule is None:
            print(f"skip {src}: not in frozen rules")
            continue
        t = time.time()
        pred = test_scores(src, D, Xf)
        pk = decode(pred, rule, D, TE, val.get("k_prior"))
        ev = L.eval_peaks(pk, D, TE, src)
        secs = time.time() - t
        tr_meta = {}
        mp = os.path.join(L.DATA, f"up2_p1a_train_{src}.json")
        if src not in ("v1", "ens") and os.path.exists(mp):
            with open(mp, encoding="utf-8") as f:
                tr_meta = json.load(f)
            secs += float(tr_meta.get("seconds", 0.0))
        params = params_of(src)
        row = dict(name={"v1": "C1_decoder_only_v1", "mtask": "C2_multitask",
                         "sslmtask": "C3_ssl_multitask",
                         "ens": "C4_ensemble_v1_mtask_ssl"}[src],
                   params=dict(src=src, sig=rule["sig"], w=rule["w"], sigma=rule["sigma"],
                               min_len=rule["min_len"], lam=rule["lam"], shift=rule["shift"],
                               seeds=tr_meta.get("seeds"), epochs=tr_meta.get("epochs"),
                               ssl_epochs=tr_meta.get("ssl_epochs")),
                   val_ari=float(rule["val_ari"]), val_bf1=float(rule["val_bf1"]),
                   test_ari=float(ev["mean_ari"]), test_bf1=float(ev["mean_bf1"]),
                   k_err=float(ev["mean_k_abs_err"]), npred=float(ev["mean_npred"]),
                   bf1_hard5=float(ev["mean_bf1_hard5"]),
                   per_env=L.by_env(ev["per_record"], D), seconds=round(float(secs), 1),
                   params_count=params,
                   per_record=[{kk: (None if isinstance(vv, float) and np.isnan(vv) else vv)
                                for kk, vv in row_i.items()}
                               for row_i in ev["per_record"]])
        cfg.append(row)
        print(f"\n{row['name']}: val ARI {row['val_ari']:.4f} bf1 {row['val_bf1']:.4f} | "
              f"TEST ARI {row['test_ari']:.4f} bf1 {row['test_bf1']:.4f} "
              f"kerr {row['k_err']:.2f} npred {row['npred']:.2f} | {row['seconds']}s")
        for v in row["per_record"]:
            print(f"  rec {v['rec']:>3} n_pred {v['n_pred']} k {v['k_true']} "
                  f"ARI {v['ari']:.3f} bf1 {v['bf1']:.3f}")

    # pick best by the same validation objective used for selection (no test peeking)
    if cfg:
        best_rule = max(cfg, key=lambda c: c["val_ari"] + 0.5 * c["val_bf1"])["name"]
    passes = bool(cfg and best_rule is not None)
    if passes:
        b = [c for c in cfg if c["name"] == best_rule][0]
        passes = bool(b["test_ari"] >= GATE["test_ari"] and b["test_bf1"] >= GATE["test_bf1"])

    out = dict(baseline=baseline, configs=cfg, best=best_rule,
               gate=GATE, passes=passes,
               notes=("选型只用验证集（obj = val ARI + 0.5*val bf1，top-5 内用 train obj 打破平局），"
                      "test 只评一次。baseline 为已发表的 v1 规则结果，用于对照；"
                      "gate 为预注册门槛，未达标如实记 passes=false。"),
               seconds_total=round(time.time() - t0, 1),
               evaluated_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    L.save_json(os.path.join(L.DATA, "up2_p1a.json"), out)
    print(f"\npasses={passes} best={best_rule}")
    print("wrote data/up2_p1a.json")


if __name__ == "__main__":
    main()