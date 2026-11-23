"""Build data/ledger.json for the backup paper: every source with sha256 + fetched_at.

Sources: the seven constraint files, the problem statement PDF, and one directory-tree
digest per archive (sorted rel-path + size, hashed; not a per-file content hash).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
# Data root is environment-driven so the package carries no machine identity:
#   set RESTOCK_DATA_ROOT to the folder where you unpacked Restocking_Problem_and_Data_EN.
import os as _os
_RESTOCK_DATA_ROOT = _os.environ.get(
    "RESTOCK_DATA_ROOT",
    _os.path.join(_os.path.expanduser("~"), "Desktop", "Restocking_Problem_and_Data_EN"),
)

import time

WS = pathlib.Path(__file__).resolve().parents[1]
DESK = pathlib.Path(_RESTOCK_DATA_ROOT)
CONS = DESK / "Restocking_Tasks_and_Constraints"
RAW = DESK / "Raw_Data"
PROB = pathlib.Path(
    r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题"
    r"\C题\2026_“ShuWei Cup”C_Problem.pdf"
)


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while block := f.read(8 << 20):
            h.update(block)
    return h.hexdigest()


def tree_digest(root: pathlib.Path) -> tuple[str, int, int]:
    h = hashlib.sha256()
    n = 0
    total = 0
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            size = p.stat().st_size
            h.update(f"{rel}\t{size}\n".encode("utf-8"))
            n += 1
            total += size
    return h.hexdigest(), n, total


def main() -> int:
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    records = []
    for p in sorted(CONS.iterdir()):
        if p.is_file():
            records.append({
                "id": f"constraint:{p.stem}",
                "kind": "file",
                "path": str(p),
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "source": "official release, Restocking_Tasks_and_Constraints",
                "fetched_at": now,
            })
    records.append({
        "id": "problem:statement",
        "kind": "file",
        "path": str(PROB),
        "bytes": PROB.stat().st_size,
        "sha256": sha256_file(PROB),
        "source": "ShuWei Cup 2026 autumn, problem C",
        "fetched_at": now,
    })
    for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
        d = RAW / ds
        digest, n, total = tree_digest(d)
        records.append({
            "id": f"dataset:{ds}",
            "kind": "dataset_tree",
            "path": str(d),
            "files": n,
            "bytes": total,
            "sha256": digest,
            "hash_scope": "sorted relative path + byte size, not per-file content",
            "source": "official release, Raw_Data",
            "fetched_at": now,
        })
    out = {
        "schema": 1,
        "built_at": now,
        "records": records,
        "note": "12 records: 7 constraint files + problem statement + 3 dataset trees.",
    }
    WS.joinpath("data").mkdir(exist_ok=True)
    WS.joinpath("data", "ledger.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"records={len(records)} bytes={WS.joinpath('data','ledger.json').stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
