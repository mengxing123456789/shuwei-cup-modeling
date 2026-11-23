import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")


def show(name, maxdepth=3):
    p = D / name
    if not p.exists():
        print(f"--- {name}: MISSING")
        return
    o = json.loads(p.read_text(encoding="utf-8"))
    print(f"--- {name} ---")
    walk(o, 0, maxdepth)
    print()


def walk(o, d, maxd):
    pad = "  " * d
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)) and d < maxd:
                if isinstance(v, list):
                    print(f"{pad}{k}: list[{len(v)}]")
                    if v and isinstance(v[0], dict) and d + 1 < maxd:
                        print(f"{pad}  [0] keys: {list(v[0].keys())}")
                        for kk, vv in v[0].items():
                            if not isinstance(vv, (dict, list)):
                                print(f"{pad}    {kk} = {vv}")
                else:
                    print(f"{pad}{k}:")
                    walk(v, d + 1, maxd)
            elif isinstance(v, list):
                print(f"{pad}{k}: list[{len(v)}] = {v[:6]}")
            else:
                print(f"{pad}{k} = {v}")
    else:
        print(f"{pad}{o}")


for n in ("up_p3_vec_check.json", "up_p1b_dual.json", "up_p1b_seed20261121.json",
          "up_p2_quantile.json", "up_p2_smoke.json", "up_video_value.json",
          "up_p1a_final.json"):
    show(n, 3)
