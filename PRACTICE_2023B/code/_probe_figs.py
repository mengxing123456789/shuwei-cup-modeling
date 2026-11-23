# -*- coding: utf-8 -*-
"""临时探针：打印 data/results_*.json 的结构，供 make_figures.py 设计取数路径。只读。"""
import json
import pathlib

P = pathlib.Path(r"E:\数学建模\PRACTICE_2023B\data")


def walk(o, path="", depth=0, maxdepth=3):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                print(f"{path}.{k}  <{type(v).__name__} len={len(v)}>")
                if depth < maxdepth:
                    walk(v, f"{path}.{k}", depth + 1, maxdepth)
            else:
                print(f"{path}.{k} = {repr(v)[:90]}")
    elif isinstance(o, list):
        print(f"{path}  list head={repr(o[:4])[:140]}")


for name in ["results_q1", "results_q2", "results_q3", "results_q4", "results_q5",
             "results_boundary", "results_binding", "results_perturb", "results_timing"]:
    d = json.loads((P / f"{name}.json").read_text(encoding="utf-8"))
    print("=" * 24, name, "=" * 24)
    walk(d, "", 0, 2)