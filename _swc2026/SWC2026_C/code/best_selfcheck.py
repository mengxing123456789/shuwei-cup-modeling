
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""交付前自检：文件存在性 + mtime + 归属（_meta 必须是我的脚本写的）+ 关键数字对账。"""
import json
import os
import time

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FILES = ["best_p1a.json", "best_p1a_k.json", "best_p1b.json", "best_p2q.json",
         "best_p3_sens.json", "best_p3_combo.json", "audit_p1a_best.json"]
for f in FILES:
    st = os.stat(os.path.join(D, f))
    print("%-22s %8d bytes  mtime %s" % (f, st.st_size,
                                         time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))))
b = json.load(open(os.path.join(D, "best_p1b.json"), encoding="utf-8"))
print("p1b _meta:", json.dumps(b["_meta"], ensure_ascii=False)[:300])
print("p1b arms:", list(b["arms"].keys()))
print("p1b B test_auc=%.4f AP=%.4f brier_iso=%.5f ece_iso=%.4f" % (
    b["arms"]["B_std_only"]["test_auc"], b["arms"]["B_std_only"]["test_ap"],
    b["arms"]["B_std_only"]["brier_iso"], b["arms"]["B_std_only"]["ece15_iso"]))
q = json.load(open(os.path.join(D, "best_p2q.json"), encoding="utf-8"))
print("p2q seconds:", q["total_seconds"], "L:", [r["L_frames"] for r in q["rows"]])
c = json.load(open(os.path.join(D, "best_p3_combo.json"), encoding="utf-8"))
w = [r for r in c["combos"] if r["tag"] == "risk:gate=.70,q_hi=.55"][0]
print("p3 winner S2=%.4f S3=%.4f" % (w["summary"]["S2"]["mean"], w["summary"]["S3"]["mean"]))