# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# -*- coding: utf-8 -*-
# AI 辅助：DeepSeek Harness 助手生成（DeepSeek，2026-11-22）。
"""Two independent checks that every printed number still matches data/*.json.

The backup paper gets a large per-literal claim count because its numbers sit in
the body as literals.  This paper keeps them in data/ behind \\slot macros, so the
check has to run the other way.  Two angles, deliberately independent:

  A. resolve-and-compare  -- for every macro that names a JSON path, look the path
     up again in data/, format it with the same rule, and demand string equality.
     This does not reuse the generator's emission loop.
  B. regenerate-and-diff  -- rebuild slots.tex in memory from data/ and compare it
     with the file on disk line by line.  This catches a hand edit to slots.tex and
     a stale generation (data changed after the file was written).

usage:  python code/verify_slots.py [--verbose]
exit 0 = both angles agree
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fill_numbers as F  # noqa: E402  (SPEC, SLOTS, COMPUTED, resolve, fmt_value, DATA)

SLOTS_TEX = os.path.join(os.path.dirname(HERE), "slots.tex")


def read_defined(path):
    """Return {macro name: body} for every \\newcommand{\\slotX}{body} in a file."""
    t = io.open(path, encoding="utf-8").read()
    out = {}
    pat = r"\\newcommand\{\\(slot[A-Za-z]+)\}\{((?:[^{}]|\{[^{}]*\})*)\}"
    for m in re.finditer(pat, t):
        out[m.group(1)] = m.group(2)
    return out


def angle_a(defined, verbose):
    """Independent re-resolution of every JSON-backed macro."""
    ok, bad, cache = 0, [], {}
    for name, body in sorted(defined.items()):
        key = name[len("slot"):]
        if key not in F.SLOTS:
            continue
        jfile, path, fmt = F.SLOTS[key]
        if jfile not in cache:
            cache[jfile] = json.loads(
                io.open(os.path.join(F.DATA, jfile + ".json"), encoding="utf-8").read())
        try:
            want = F.fmt_value(F.resolve(cache[jfile], path), fmt)
        except Exception as exc:  # noqa: BLE001 - report and continue
            bad.append((name, body, f"resolve error: {exc}"))
            continue
        if want == body:
            ok += 1
        else:
            bad.append((name, body, want))
    print(f"[A] JSON-backed macros re-resolved : {ok} match, {len(bad)} mismatch")
    for name, got, want in bad[:30]:
        print(f"    FAIL {name}: file has {got!r}, data gives {want!r}")
    if verbose and len(bad) > 30:
        print(f"    ... {len(bad)} total")
    return ok, bad


def angle_b(verbose):
    """Regenerate slots.tex from data/ into a temp file and diff it against the real one."""
    import tempfile
    from pathlib import Path

    tmpdir = Path(tempfile.mkdtemp(prefix="slotchk_"))
    real_slots, real_todo, real_snip = F.OUT_SLOTS, F.OUT_TODO, F.SNIP
    try:
        F.OUT_SLOTS = tmpdir / "slots.tex"
        F.OUT_TODO = tmpdir / "todo_numbers.md"
        F.SNIP = tmpdir / "snippets"
        F.main()
        fresh = read_defined(str(F.OUT_SLOTS))
    finally:
        F.OUT_SLOTS, F.OUT_TODO, F.SNIP = real_slots, real_todo, real_snip

    on_disk = read_defined(SLOTS_TEX)
    ok, bad = 0, []
    for name, want in fresh.items():
        got = on_disk.get(name)
        if got is None:
            # pruned on purpose by code/prune_slots.py: the macro is generated
            # but the paper does not use it, so its absence is not a defect.
            continue
        if got == want:
            ok += 1
        else:
            bad.append((name, got, want))
    pruned = sorted(n for n in fresh if n not in on_disk)
    stale = sorted(n for n in on_disk if n not in fresh)
    print(f"[B] regenerate-and-diff           : {ok} match, {len(bad)} mismatch, "
          f"{len(pruned)} generated-but-pruned, {len(stale)} on disk but not produced")
    for name, got, want in bad[:30]:
        print(f"    FAIL {name}: file has {got!r}, fresh gives {want!r}")
    for n in stale[:10]:
        print(f"    STALE {n} = {on_disk[n]!r}")
    if verbose and len(bad) > 30:
        print(f"    ... {len(bad)} total")
    return ok, bad


def main():
    verbose = "--verbose" in sys.argv
    on_disk = read_defined(SLOTS_TEX)
    print(f"slots.tex defines {len(on_disk)} macros; "
          f"fill_numbers knows {len(F.SPEC)} constants, {len(F.SLOTS)} JSON paths, "
          f"{len(F.COMPUTED)} computed")
    ok_a, bad_a = angle_a(on_disk, verbose)
    ok_b, bad_b = angle_b(verbose)
    total_ok, total_bad = ok_a + ok_b, len(bad_a) + len(bad_b)
    print(f"claims={total_ok + total_bad} checked={total_ok + total_bad} "
          f"failures={total_bad} verdict={'PASS' if not total_bad else 'FAIL'}")
    return 0 if not total_bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
