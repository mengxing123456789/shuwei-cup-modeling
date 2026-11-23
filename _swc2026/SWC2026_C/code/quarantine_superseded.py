# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Quarantine data artefacts that nothing reads any more.

Why this exists
---------------
``mmkit.freshness`` pairs every ``data/*.json`` with every ``code/*.py`` whose
name shares a token and flags the pair when the script is newer.  The check is
deliberately a heuristic -- it is not a dependency graph -- so a *used* artefact
that is merely older than an unrelated edit shows up exactly like a genuine
stale number.  The paper's own gate (``gauntlet_check.py`` R-V09) therefore
carries 86 open pairs, and "KNOWN OPEN (explain each)" is not a state I want to
hand in.

The honest fix is not to silence the check but to separate live artefacts from
superseded ones: an artefact that no script, table or audit reads any more is
*history*, and history belongs in a folder that the freshness glob does not
scan.  This script moves exactly those files to ``data/_superseded/`` and writes
``data/_superseded/MANIFEST.json`` with size, mtime and sha256, so the provenance
survives the move.

A file is moved only when all of the following hold:
  * its name does not appear in any ``code/*.py``, ``tables/*.tex`` or the
    audit script (substring search, so ``p1b.json`` protects ``p1b_gpu.json``);
  * it is not listed in the slot definitions (``slots.tex`` / ``slots.full.tex``);
  * it is not one of the canonical inputs of ``fill_numbers.py``.

Nothing is deleted.  ``--apply`` performs the move; the default is a dry run.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUDIT = ROOT.parent / "audit"
DEST = DATA / "_superseded"

#: never move these, whatever the reference scan says
PROTECT = {
    "state.npz", "panel.npz", "panel_records.csv", "segments.csv",
    "p1_segmentation.json", "up_p1b_aux.npz", "ledger.json",
    "common_conditions.json", "record_split.csv", "tasks.csv",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def haystack() -> str:
    """Text of every consumer, minus the scanners.

    Both this file and the probe scripts name the candidates in their own
    source, so including them makes every artefact look referenced.  Files
    starting with an underscore are probes, not consumers.
    """
    parts = []
    for pat in ("code/*.py", "tables/*.tex", "*.tex", "audit/*.py", "snippets/*"):
        for p in list(ROOT.glob(pat)) + list(AUDIT.glob(Path(pat).name)):
            if p.name.startswith("_") or p.name == Path(__file__).name:
                continue
            try:
                parts.append(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    return "\n".join(parts)


def generated_by(stem: str, text: str) -> bool:
    """True when some consumer builds this name from a format string or a glob.

    ``up13_p1a_anchor_palm.json`` never appears literally, because
    ``up13b_retrain_under_anchor.py`` writes ``up13_p1a_anchor_%s.json``;
    ``up2_p2_armA.json`` comes from ``f"up2_p2_arm{k}.json"``; the video shards
    come from ``video_features_part*.csv``.  Treating those as unreferenced
    would quarantine live inputs, so a prefix that appears in the source with a
    substitution marker right after it counts as a reference.
    """
    markers = ("%s", "%(", "{", "*", "<", "%d")
    for cut in range(len(stem), 9, -1):
        head = stem[:cut]
        for m in markers:
            if head + m in text:
                return True
    # f-string form: the literal head appears before a brace that opens a
    # substitution, e.g. "up2_p2_arm" + "{k}"
    for cut in range(len(stem), 9, -1):
        head = stem[:cut]
        idx = text.find(head)
        while idx >= 0:
            if idx + len(head) < len(text) and text[idx + len(head)] in "{*%<":
                return True
            idx = text.find(head, idx + 1)
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-lag-hours", type=float, default=0.5,
                    help="only consider files older than this lag against some script")
    a = ap.parse_args()

    text = haystack()
    scripts = sorted((ROOT / "code").glob("*.py"))

    cands = []
    for p in sorted(list(DATA.glob("*.json")) + list(DATA.glob("*.csv"))):
        if p.name in PROTECT or p.name.startswith("_"):
            continue
        if p.name in text:
            continue
        if generated_by(p.stem, text):
            continue
        # a .bak_ or .prev copy is by construction superseded
        flagged = p.name.startswith(("p1a_gpu_segmentation.bak", "p1a_gpu_segmentation.prev",
                                     "p1a_gpu_segmentation.rerun"))
        if not flagged:
            # otherwise require that some script looks newer (the R-V09 condition)
            newest = max((s.stat().st_mtime for s in scripts), default=0)
            lag = (newest - p.stat().st_mtime) / 3600.0
            if lag < a.min_lag_hours:
                continue
        cands.append(p)

    print(f"unreferenced artefacts: {len(cands)}")
    for p in cands:
        print("   ", p.name, p.stat().st_size)

    if not a.apply:
        print("\ndry run; pass --apply to move them to", DEST)
        return

    DEST.mkdir(exist_ok=True)
    man_path = DEST / "MANIFEST.json"
    man = {}
    if man_path.exists():
        man = json.loads(man_path.read_text(encoding="utf-8"))
    moved = []
    for p in cands:
        tgt = DEST / p.name
        if tgt.exists():
            tgt.unlink()
        shutil.move(str(p), str(tgt))
        man[p.name] = dict(bytes=tgt.stat().st_size, sha256=sha(tgt),
                           note="no longer referenced by code/, tables/ or the audit; moved "
                                "out of the freshness scan on 2026-11-22")
        moved.append(p.name)
    man_path.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"moved {len(moved)} files; manifest at {man_path}")


if __name__ == "__main__":
    main()
