
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# -*- coding: utf-8 -*-
"""Shared paths / loaders for SWC2026 C. All heavy reads go through here."""
import os, glob, json
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(_HERE)
# Portable by default: the package can be extracted anywhere.  Set MM_ROOT to the
# directory that holds the raw kaggle tree (``cdata``) when re-running from source;
# MM_CDATA overrides the raw-data directory itself.
ROOT = os.environ.get("MM_ROOT") or os.path.dirname(PROJ)
CD = os.environ.get("MM_CDATA") or os.path.join(ROOT, "cdata")
DATA = os.path.join(PROJ, "data")
FIG = os.path.join(PROJ, "figures")


def _resolve_att():
    """Official attachments root.

    The organiser's 2026-11-20 notice points at
    ``Restocking_Tasks_and_Constraints/source_segment_index.csv`` and
    ``record_split.csv``.  ``MM_C_PROBLEM_ROOT`` always wins; otherwise the
    package-relative ``problem/`` copy and two common local layouts are tried.
    """
    env = os.environ.get("MM_C_PROBLEM_ROOT")
    if env:
        return env
    tail = os.path.join("Restocking_Tasks_and_Constraints")
    candidates = [
        os.path.join(PROJ, "problem", "Restocking_Problem_and_Data_EN", tail),
        os.path.join(ROOT, "cdata", "Restocking_Problem_and_Data_EN", tail),
        os.path.join(r"Restocking_Problem_and_Data_EN", tail),
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