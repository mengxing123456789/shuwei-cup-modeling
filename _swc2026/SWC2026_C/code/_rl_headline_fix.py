# -*- coding: utf-8 -*-
"""One-off: shorten the RL ledger headline so the GPU table fits the line."""
import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "data" / "up_p3_rl.json"
d = json.loads(p.read_text(encoding="utf-8"))
d["_meta"]["ledger"]["headline"] = "S2 +5.0 / S3 -6.9 pt, fail"
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(d["_meta"]["ledger"]["headline"])
