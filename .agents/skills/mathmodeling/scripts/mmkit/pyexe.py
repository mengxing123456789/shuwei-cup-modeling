"""Locate a Python interpreter that has the scientific stack, without hard-coding a drive.

Why this exists
---------------
Every script in this skill used to start with

    PY = Path(r"python")

which works on exactly one machine.  The moment the workspace moves to another
drive, or is cloned onto a different computer, the whole pipeline dies at the
first subprocess with `FileNotFoundError` — and it dies *after* the expensive
part has already run.

Resolution order (first hit wins)
---------------------------------
1. ``MM_PY``               — explicit override, e.g. ``set MM_PY=C:\\py311\\python.exe``
2. the interpreter running *this* process, if it can import numpy
3. a short list of conventional venv locations relative to the workspace
4. ``python`` on PATH, if it can import numpy
5. the interpreter running this process anyway (it may still work for
   pure-stdlib scripts)

Callers get a ``str`` path plus a bool saying whether the stack was verified,
so a brief can print an honest warning instead of silently degrading.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Modules that every subprocess in this skill needs.  pymupdf is optional: the
# figure-font probe is the only consumer, and it degrades to SKIP without it.
STACK = ("numpy", "pandas", "matplotlib")


def _can_import(exe: str, mods: tuple[str, ...] = STACK) -> bool:
    code = "import " + ", ".join(mods)
    try:
        r = subprocess.run([exe, "-c", code], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _workspace_root() -> Path:
    for probe in Path(__file__).resolve().parents:
        if (probe / ".agents" / "skills").is_dir():
            return probe
    return Path(__file__).resolve().parents[3]


def _candidates() -> list[str]:
    out: list[str] = []

    env = os.environ.get("MM_PY")
    if env:
        out.append(env)

    out.append(sys.executable)

    ws = _workspace_root()
    for rel in (
        "envs/mathmodel/python.exe",          # Windows layout of the original box
        "envs/mathmodel/bin/python",          # same, POSIX
        ".venv/Scripts/python.exe",
        ".venv/bin/python",
        "venv/Scripts/python.exe",
        "venv/bin/python",
    ):
        out.append(str(ws / rel))

    for name in ("python3", "python"):
        hit = shutil.which(name)
        if hit:
            out.append(hit)

    seen, uniq = set(), []
    for c in out:
        key = os.path.normcase(os.path.abspath(c))
        if key not in seen and os.path.exists(c):
            seen.add(key)
            uniq.append(c)
    return uniq


def resolve_py(verify: bool = True) -> tuple[str, bool]:
    """Return ``(executable, has_stack)``.

    ``verify=False`` skips the import probe and returns the first existing
    candidate — use it where the call is pure stdlib and speed matters.
    """
    cands = _candidates()
    if not verify:
        return (cands[0] if cands else sys.executable, False)
    for c in cands:
        if _can_import(c):
            return c, True
    return (cands[0] if cands else sys.executable, False)


def py() -> str:
    """Just the path, for the common case."""
    return resolve_py()[0]


def mupdf_py() -> str:
    """Interpreter that can import pymupdf (falls back to the general one)."""
    for c in _candidates():
        if _can_import(c, ("numpy", "fitz")):
            return c
    return py()


if __name__ == "__main__":
    exe, ok = resolve_py()
    print(f"python : {exe}")
    print(f"stack  : {'ok' if ok else 'MISSING — set MM_PY to a Python with numpy/pandas/matplotlib'}")
