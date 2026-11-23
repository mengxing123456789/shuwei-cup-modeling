import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\05_audit\pages_now.json")
d = json.loads(p.read_text(encoding="utf-8"))
pages = d if isinstance(d, list) else d.get("pages", [])
for r in pages:
    if isinstance(r, dict):
        txt = r.get("text", "") or ""
        print(r.get("page"), len(txt), (r.get("head", "") or "")[:70].replace("\n", " "))
