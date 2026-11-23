# -*- coding: utf-8 -*-
"""Package the alternative paper into the three submission files.

Same naming rule as the main paper: `problem+team.pdf`, `+cns.pdf`, `+fj.zip`.
The PDF is copied rather than recompiled, so its bytes are identical to
`main.pdf` and the sha256 in `review/00-metrics.md` stays valid.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEAM = "SWBMCM2634892"
PROBLEM = "C"
STEM = f"{PROBLEM}{TEAM}"

# Derived caches: reproducible from the released archives and from the JSONs that
# are already in the archive, and together they are 30.9 MB — more than the whole
# 20 MB budget. Excluding them keeps the support archive under the limit without
# removing anything a reader would need to reproduce a number.
EXCLUDE = {
    "data/panel_alt.npz",          # 29.76 MB, rebuilt by code/alt_p2_data.py in 41 s
    "data/results_swc2026.json",   # 1.11 MB, merged by code/alt_stage.py from the others
}


def team_number() -> str:
    tex = (ROOT / "main.tex").read_text(encoding="utf-8")
    m = re.search(r"\\baominghao\{([^}]*)\}", tex)
    if not m:
        return ""
    got = m.group(1).strip()
    if "XXXX" in got or "placeholder" in got.lower():
        return ""
    return got


def sha(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main() -> int:
    tn = team_number()
    print(f"team number: {tn or '(not filled)'}")
    if tn != TEAM:
        print(f"WARN: expected {TEAM}, got {tn!r}")

    pdf = ROOT / "main.pdf"
    if not pdf.exists():
        print("main.pdf missing")
        return 2
    dst = ROOT / f"{STEM}.pdf"
    dst.write_bytes(pdf.read_bytes())
    print(f"paper   {dst.name}  {dst.stat().st_size:,} B  sha {sha(dst)}")

    cns = ROOT / f"{STEM}cns.pdf"
    if cns.exists():
        print(f"letter  {cns.name}  {cns.stat().st_size:,} B  (signature is the author's step)")
    else:
        print(f"letter  {cns.name}  MISSING")

    zpath = ROOT / f"{STEM}fj.zip"
    entries = 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for sub in ("code", "data", "figures", "out", "review", "tables"):
            d = ROOT / sub
            if not d.is_dir():
                continue
            for f in sorted(d.rglob("*")):
                if not f.is_file():
                    continue
                if "_scratch" in f.parts or "__pycache__" in f.parts:
                    continue
                rel = f.relative_to(ROOT).as_posix()
                if rel in EXCLUDE:
                    continue
                z.write(f, rel)
                entries += 1
        for name in ("main.tex", "main.pdf", "README_备用.md"):
            f = ROOT / name
            if f.is_file():
                z.write(f, name)
                entries += 1
    print(f"support {zpath.name}  {zpath.stat().st_size:,} B  {entries} entries")

    total = dst.stat().st_size + zpath.stat().st_size
    if cns.exists():
        total += cns.stat().st_size
    print(f"total   {total:,} B  ({total / 1048576:.2f} MB)  limit 20 MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
