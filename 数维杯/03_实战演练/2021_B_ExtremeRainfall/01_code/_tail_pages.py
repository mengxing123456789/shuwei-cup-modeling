import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\05_audit\paper_text.txt")
t = p.read_text(encoding="utf-8")
parts = re.split(r"=== PAGE (\d+) ===", t)
pages = {}
for i in range(1, len(parts), 2):
    pages[int(parts[i])] = parts[i + 1]
print("pages:", min(pages), max(pages), len(pages))
for k in sorted(pages):
    if 20 <= k <= 24:
        body = pages[k].strip()
        print(f"--- page {k}: {len(body)} chars")
        print("HEAD:", body[:200].replace("\n", " | "))
        print("TAIL:", body[-260:].replace("\n", " | "))
