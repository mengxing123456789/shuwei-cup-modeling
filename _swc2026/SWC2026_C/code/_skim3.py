# AI 辅助：DeepSeek Harness 助手生成的一次性键名检查脚本。
# -*- coding: utf-8 -*-
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def walk(o, path="", depth=0):
    if depth > 2:
        return
    if isinstance(o, dict):
        for k, v in list(o.items())[:16]:
            if isinstance(v, (dict, list)):
                walk(v, f"{path}/{k}", depth + 1)
            else:
                print(f"  {path}/{k} = {v}")


for name in ("p2_frontier", "p3_oracle_same_rule", "p2_reliability_weight"):
    p = ROOT / "data" / f"{name}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    print("=== ", name, list(d.keys())[:12])
    walk(d)