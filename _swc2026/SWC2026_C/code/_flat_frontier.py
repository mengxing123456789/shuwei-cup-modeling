# AI 辅助：DeepSeek Harness 助手生成的一次性补丁，把前沿表拍平成标量供槽位直接取用。
# -*- coding: utf-8 -*-
"""p2_frontier.json 的 `table` 是列表，槽位解析器只认键路径与 @k=v 选择器。
这里补一个 `_flat` 字典，避免在正文槽位里依赖列表下标（下标一换就静默取错数）。"""
import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "data" / "p2_frontier.json"
d = json.loads(P.read_text(encoding="utf-8"))
flat = {}
for row in d["table"]:
    flat[f"{row['policy']}_rms_cm"] = row["rms_cm"]
    flat[f"{row['policy']}_cost_units"] = row["cost_units"]
    flat[f"{row['policy']}_lead_s"] = row["lead_s"]
    flat[f"{row['policy']}_requests"] = row["requests"]
d["_flat"] = flat
P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(flat, indent=1, ensure_ascii=False))