import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")


def dump(name, depth=2):
    p = D / name
    print(f"\n=== {name} ===")
    if not p.exists():
        print("MISSING")
        return
    d = json.loads(p.read_text(encoding="utf-8"))

    def walk(o, dd, maxd, pad=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, dict) and dd < maxd:
                    print(f"{pad}{k}:")
                    walk(v, dd + 1, maxd, pad + "  ")
                elif isinstance(v, list):
                    print(f"{pad}{k}: list[{len(v)}] {json.dumps(v[:3], ensure_ascii=False)[:200]}")
                else:
                    print(f"{pad}{k} = {v}")
        else:
            print(pad, o)

    walk(d, 0, depth)


for n in ("up_p2_quantile.json", "up_p2_smoke.json", "up_video_value.json", "up_p1a_final.json"):
    dump(n, 2)
