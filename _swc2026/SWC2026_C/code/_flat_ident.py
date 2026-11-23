# AI 辅助：DeepSeek Harness 助手生成的一次性补丁，把可辨识性两张表的结论拍平成标量。
# -*- coding: utf-8 -*-
import json
import pathlib

D = pathlib.Path(__file__).resolve().parent.parent / "data"

p2 = D / "phase_identifiability2.json"
d = json.loads(p2.read_text(encoding="utf-8"))
rhos = [abs(v["spearman"]) for v in d["table"].values()]
d["summary"] = dict(
    max_abs_spearman=max(rhos),
    min_p=min(v["p"] for v in d["table"].values()),
    n_boundaries=d["_meta"]["n_boundaries"],
    rate_low_min=min(v["rate_low"] for v in d["table"].values()),
    rate_high_max=max(v["rate_high"] for v in d["table"].values()),
)
p2.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("identifiability2 summary:", d["summary"])

p1 = D / "phase_identifiability.json"
d1 = json.loads(p1.read_text(encoding="utf-8"))
d1["summary"]["max_abs_spearman"] = max(abs(v["spearman"]) for v in d1["table"].values()) if "table" in d1 else abs(d1["summary"]["spearman_rho"])
p1.write_text(json.dumps(d1, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("identifiability1 summary keys:", list(d1["summary"].keys()))