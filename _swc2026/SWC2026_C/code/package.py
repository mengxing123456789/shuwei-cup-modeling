
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# -*- coding: utf-8 -*-
"""Freeze the three submission files for team CSWBMCM2634892.

Produces
    CSWBMCM2634892.pdf      the paper (body <= 25 pages, appendices after it)
    CSWBMCM2634892cns.pdf   the commitment letter (needs the three signatures)
    CSWBMCM2634892fj.zip    the support package: code, sources, figures, numbers

Run after `fill_numbers.py` + two xelatex passes. Big array files are left out on
purpose: README_FJ.md says which script rebuilds each one, and the official cap is
20 MB for paper plus attachments.
"""
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM = "CSWBMCM2634892"

# 1. paper ----------------------------------------------------------------------
paper = ROOT / "main.pdf"
dst_paper = ROOT / f"{TEAM}.pdf"
assert paper.exists(), "main.pdf missing"
shutil.copy2(paper, dst_paper)

# 2. commitment letter ----------------------------------------------------------
cns = ROOT / f"{TEAM}cns.pdf"
assert cns.exists(), "commitment letter missing"

# 3. support package ------------------------------------------------------------
ZIP = ROOT / f"{TEAM}fj.zip"
SKIP_DIRS = {"__pycache__", "models", ".ipynb_checkpoints", "_superseded", "_unused"}
SKIP_SUFFIX = {".npz", ".npy", ".pt", ".pyc", ".aux", ".log", ".out", ".toc", ".bak"}
# Working notes and stale documentation are not part of the submission package.
EXCLUDE_FILES = {
    "data/pre_p2_tables.md",
    "data/up_p2_final.txt",
    "figures/MANIFEST.md",
}


def wanted(path: Path) -> bool:
    if path.suffix in SKIP_SUFFIX:
        return False
    if ".bak" in path.name or ".broken_" in path.name:
        return False  # editor/iteration backups are not part of the release
    if path.name.startswith("_") and path.suffix == ".py":
        return False  # one-off patch helpers, not part of the reproduction chain
    try:
        if path.relative_to(ROOT).as_posix() in EXCLUDE_FILES:
            return False
    except ValueError:
        pass
    return True


entries = []
for sub in ("code", "figures", "snippets", "data", "tables", "problem"):
    base = ROOT / sub
    if not base.is_dir():
        continue
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(("finalrep_", "shadow_anchor_"))
        ]
        for fn in filenames:
            p = Path(dirpath) / fn
            if wanted(p):
                entries.append(p)

# tables/ must travel with main.tex: the paper \\input{}s every one of them, so a
# package without them cannot be recompiled from source at all.
for extra in ("main.tex", "slots.tex", "slots.full.tex", "main.bbl", "README_FJ.md", "requirements.txt", "data/derived_manifest.json",
              "swmcmthesis.cls", "swmcmthesis.cfg", f"{TEAM}cns.tex"):
    p = ROOT / extra
    if p.exists():
        entries.append(p)

if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(set(entries)):
        z.write(p, p.relative_to(ROOT).as_posix())

size = ZIP.stat().st_size
with zipfile.ZipFile(ZIP) as z:
    n = len(z.namelist())
    names = z.namelist()

print(f"paper   : {dst_paper.name} {dst_paper.stat().st_size:,} B")
print(f"letter  : {cns.name} {cns.stat().st_size:,} B")
print(f"package : {ZIP.name} {size:,} B  ({size / 2**20:.2f} MB) / {n} entries")
print(f"total   : {(dst_paper.stat().st_size + cns.stat().st_size + size) / 2**20:.2f} MB (cap 20 MB)")

missing = [e for e in ("code/p3_stochastic_schedule.py", "code/p1a_gpu_segmentation.py",
                       "code/p3_improved_search.py", "code/p2_masked.py", "code/p1b_calib.py",
                       "code/fill_numbers.py", "code/verify_numbers.py", "code/page_report.py",
                       "tables/app_n.tex", "tables/app_m.tex", "tables/tab_p1_anchor.tex",
                       "tables/tab_p3_threelevel.tex", "tables/tab_loto.tex",
                       "README_FJ.md", "snippets/reproduce.ps1", "requirements.txt", "data/derived_manifest.json") if e not in names]
print("absent from package:", missing if missing else "none")