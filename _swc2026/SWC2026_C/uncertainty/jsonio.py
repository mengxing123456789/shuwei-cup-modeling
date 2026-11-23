"""JSON helpers. All U-layer products are UTF-8 without BOM."""
from __future__ import annotations

import dataclasses
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

def _att_dir():
    """任务附件目录：环境变量优先，其次仓库内 problem/ 副本。"""
    import os as _os
    env = _os.environ.get("SWC_ATT_DIR") or _os.environ.get("MM_C_PROBLEM_ROOT")
    if env and _os.path.isdir(env):
        return _os.path.abspath(env)
    here = _os.path.dirname(_os.path.abspath(__file__))
    for _ in range(8):
        cand = _os.path.join(
            here, "problem", "Restocking_Problem_and_Data_EN", "Restocking_Tasks_and_Constraints")
        if _os.path.isdir(cand):
            return cand
        nd = _os.path.dirname(here)
        if nd == here:
            break
        here = nd
    return _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)),
        "problem", "Restocking_Problem_and_Data_EN", "Restocking_Tasks_and_Constraints")


PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data"
CODE = PROJECT / "code"
DEFAULT_ATT_DIR = Path(_att_dir())


def att_dir() -> Path:
    p = Path(os.environ.get("SWC_ATT_DIR", str(DEFAULT_ATT_DIR)))
    if not p.exists():
        raise FileNotFoundError(f"task attachment directory not found: {p}")
    return p


def jsonable(obj: Any) -> Any:
    """Recursively convert numpy / dataclass / Path values to JSON-safe types."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, np.ndarray):
        return [jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if dataclasses.is_dataclass(obj):
        return jsonable(dataclasses.asdict(obj))
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def write_json(path: str | Path, obj: Any) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = DATA / p
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(jsonable(obj), f, ensure_ascii=False, indent=2)
        f.write("\n")
    return p


def read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.is_absolute():
        p = DATA / p
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)