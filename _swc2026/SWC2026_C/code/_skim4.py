# AI 辅助：DeepSeek Harness 助手生成的一次性键名检查脚本（frontier 表 + 可靠性臂）。
# -*- coding: utf-8 -*-
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

fr = json.loads((ROOT / "data" / "p2_frontier.json").read_text(encoding="utf-8"))
print("frontier.table:", json.dumps(fr["table"], ensure_ascii=False, indent=1)[:1200])
print("frontier.dominance:", json.dumps(fr.get("dominance"), ensure_ascii=False)[:600])

rw = json.loads((ROOT / "data" / "p2_reliability_weight.json").read_text(encoding="utf-8"))
for k, v in rw["arms"].items():
    print(k, {kk: vv for kk, vv in v.items() if kk != "per_record_cm"})
print("cmp keys:", list(rw["comparisons"].keys()))