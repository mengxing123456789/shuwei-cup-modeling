# -*- coding: utf-8 -*-
"""Check what p3_official_audit cells carry (looking for elapsed / censored)."""
import json
from pathlib import Path

D = Path(r"E:\数学建模\_swc2026\SWC2026_C\data")
j = json.loads((D / "p3_official_audit.json").read_text(encoding="utf-8"))
cells = j["cells"]
print("cells type:", type(cells), "len:", len(cells))
c0 = cells[0] if isinstance(cells, list) else next(iter(cells.values()))
print("cell keys:", list(c0.keys()))
print(json.dumps(c0, indent=1)[:1500])
