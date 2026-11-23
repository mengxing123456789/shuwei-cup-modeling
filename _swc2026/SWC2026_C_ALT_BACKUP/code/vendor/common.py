
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness, a command-line coding agent (DeepSeek),
# 18-20 November 2026; every number this file produces was re-executed by the
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Shared paths / loaders for SWC2026 C. All heavy reads go through here."""
import os, glob, json
# Data root is environment-driven so the package carries no machine identity:
#   set RESTOCK_DATA_ROOT to the folder where you unpacked Restocking_Problem_and_Data_EN.
import os as _os
_RESTOCK_DATA_ROOT = _os.environ.get(
    "RESTOCK_DATA_ROOT",
    _os.path.join(_os.path.expanduser("~"), "Desktop", "Restocking_Problem_and_Data_EN"),
)

import numpy as np
import pandas as pd

ROOT = r"E:\数学建模\_swc2026"
CD = os.path.join(ROOT, "cdata")
PROJ = os.path.join(ROOT, "SWC2026_C")
DATA = os.path.join(PROJ, "data")
FIG = os.path.join(PROJ, "figures")


def _resolve_att():
    """Official attachments root, preferring the copy the user keeps on Desktop.

    The organiser's 2026-11-20 notice points at
    ``Restocking_Tasks_and_Constraints/source_segment_index.csv`` and
    ``record_split.csv``; the two copies on this machine are byte-identical.
    An explicit ``MM_C_PROBLEM_ROOT`` always wins.
    """
    env = os.environ.get("MM_C_PROBLEM_ROOT")
    if env:
        return env
    tail = os.path.join("Restocking_Tasks_and_Constraints")
    candidates = [
        os.path.join(_RESTOCK_DATA_ROOT, tail),
        _os.environ.get("RESTOCK_PROBLEM_ROOT",
            _os.path.join(_RESTOCK_DATA_ROOT, "C_Problem_Data", "C_Problem_Data",
                          "Restocking_Problem_and_Data_EN", "Restocking_Problem_and_Data_EN")),

    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "source_segment_index.csv")):
            return c
    return candidates[0]


ATT = _resolve_att()
DATASETS = ["EgoDemo", "EgoPro", "EgoStandard"]


def ensure_dirs():
    for d in (DATA, FIG):
        os.makedirs(d, exist_ok=True)


def load_index():
    idx = pd.read_csv(os.path.join(ATT, "source_segment_index.csv"), encoding="utf-8-sig")
    idx["sample"] = idx["sample"].astype(str)
    return idx


def load_split():
    sp = pd.read_csv(os.path.join(ATT, "record_split.csv"), encoding="utf-8-sig")
    sp["episode_uuid"] = sp["episode_uuid"].astype(str)
    return sp


def load_tasks():
    return pd.read_csv(os.path.join(ATT, "tasks.csv"), encoding="utf-8-sig")


def load_zones():
    return pd.read_csv(os.path.join(ATT, "service_zones.csv"), encoding="utf-8-sig")


def load_conditions():
    with open(os.path.join(ATT, "common_conditions.json"), encoding="utf-8") as f:
        return json.load(f)


def record_dirs():
    """Yield (dataset, sample, path)."""
    for ds in DATASETS:
        for p in sorted(glob.glob(os.path.join(CD, ds, "*"))):
            if os.path.isdir(p):
                yield ds, os.path.basename(p), p


def quat_to_R(q):
    """(w,x,y,z) -> rotation matrix. Accepts (...,4), returns (...,3,3)."""
    q = np.asarray(q, dtype=np.float64)
    q = q / (np.linalg.norm(q, axis=-1, keepdims=True) + 1e-12)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    R = np.empty(q.shape[:-1] + (3, 3), dtype=np.float64)
    R[..., 0, 0] = 1 - 2 * (y * y + z * z)
    R[..., 0, 1] = 2 * (x * y - z * w)
    R[..., 0, 2] = 2 * (x * z + y * w)
    R[..., 1, 0] = 2 * (x * y + z * w)
    R[..., 1, 1] = 1 - 2 * (x * x + z * z)
    R[..., 1, 2] = 2 * (y * z - x * w)
    R[..., 2, 0] = 2 * (x * z - y * w)
    R[..., 2, 1] = 2 * (y * z + x * w)
    R[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def write_json(name, obj):
    ensure_dirs()
    p = os.path.join(DATA, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p