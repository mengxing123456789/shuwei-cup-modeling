import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
o = json.loads((D / "up_p1b_dual.json").read_text(encoding="utf-8"))
arms = o["arms"]
items = arms.values() if isinstance(arms, dict) else arms
print("=== arms summary ===")
for a in items:
    print(f"{a.get('arm'):28s} valAUC {a.get('val_auc', 0):.6f} valAP {a.get('val_ap', 0):.6f} "
          f"testAUC {a.get('test_auc', 0):.6f} testAP {a.get('test_ap', 0):.6f} "
          f"lift {a.get('test_ap_lift', 0):.3f} best_ep {a.get('best_epoch')} sec {a.get('seconds')}")
    pe = a.get("per_env") or []
    print("   per_env:", json.dumps(pe, ensure_ascii=False)[:400])
print()
for k, v in o.items():
    if k not in ("_meta", "baseline", "protocol", "arms"):
        print(k, "=", json.dumps(v, ensure_ascii=False)[:1200])
