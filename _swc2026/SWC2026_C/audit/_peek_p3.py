import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
p = D / "up_p3_two_regime.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("top keys:", list(d.keys()))
for k, v in d.items():
    if isinstance(v, dict):
        print(f"\n{k}: dict keys {list(v.keys())[:20]}")
        for kk, vv in list(v.items())[:4]:
            print("   ", kk, "->", json.dumps(vv, ensure_ascii=False)[:300])
    elif isinstance(v, list):
        print(f"\n{k}: list[{len(v)}]")
        print("   [0]:", json.dumps(v[0], ensure_ascii=False)[:500])
    else:
        print(f"\n{k} = {v}")
