"""全量审计：三个 ZIP 的每一个文件、每一个字节，以及每一路视频的容器元数据。

边界写死：本脚本不逐帧理解画面语义；视频做全字节 SHA-256、OpenCV 容器参数、
首/中/末三帧解码抽检，并与对应数值表/帧索引行数对齐。非视频文件逐一 SHA-256
对照解压副本，CSV 全量解析、JSON 全量解析、Parquet 读 schema 与行数。

复现：python code\audit_all_data.py
"""

from __future__ import annotations

def _corpus_root():
    """语料根：MM_CORPUS_ROOT > 向上找含 corpus/problems 的一级 > 旧 AsterLink 兜底。"""
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("MM_CORPUS_ROOT")
    if env:
        return env
    for _probe in _P(__file__).resolve().parents:
        if (_probe / "corpus" / "problems").is_dir():
            return str(_probe / "corpus")
    return r"C:\Users\29900\Downloads\AsterLink"

import collections
import hashlib
import json
import os
import pathlib
import tempfile
import time

import cv2
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

WS = pathlib.Path(__file__).resolve().parents[1]
RAW = WS / "data" / "raw"
SRC = pathlib.Path(
    _corpus_root() + r"\C_Problem_Data\C_Problem_Data"
    r"\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Raw_Data"
)
OUT = WS / "data" / "full_audit.json"
CHUNK = 8 << 20


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def expected_frames(local: pathlib.Path, dataset: str, channel: str) -> int:
    if dataset == "EgoDemo":
        return int(pq.ParquetFile(local / "data/chunk-000/file-000.parquet").metadata.num_rows)
    frame_csv = local / "videos" / f"{channel}_frames.csv"
    if frame_csv.exists():
        return int(len(pd.read_csv(frame_csv, usecols=[0])))
    return int(len(pd.read_csv(local / "tables/pose_left_hand.csv", usecols=[0])))


def probe_video(path: pathlib.Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"open": False}
    n = int(round(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = int(round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    height = int(round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    decoded = []
    for pos in sorted({0, max(0, n // 2), max(0, n - 1)}):
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        decoded.append({"position": pos, "ok": bool(ok and frame is not None and frame.size > 0)})
    cap.release()
    return {
        "open": True,
        "frames": n,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_s": n / fps if fps > 0 else None,
        "decoded_samples": decoded,
    }


def main() -> int:
    started = time.time()
    result = {
        "scope": "every byte of all ZIP members; all non-video parsed; video metadata plus first/middle/last decode samples",
        "not_done": "no frame-by-frame semantic viewing of the videos; no claim that image content was manually reviewed",
        "archives": {},
        "errors": [],
        "warnings": [],
    }
    totals = collections.Counter()
    video_rows = []
    payload_hashes = collections.defaultdict(list)

    with tempfile.TemporaryDirectory(prefix="shuwei2026_video_audit_") as tmp_s:
        tmp = pathlib.Path(tmp_s)
        for archive in sorted(SRC.glob("*.zip")):
            dataset = archive.stem
            print(f"[{dataset}] reading {archive.name}", flush=True)
            ar = {"members": 0, "bytes": 0, "videos": 0, "video_bytes": 0,
                  "nonvideo": 0, "nonvideo_bytes": 0, "sha256_mismatch": 0,
                  "parse_errors": 0, "video_open_errors": 0,
                  "video_sample_decode_errors": 0, "frame_count_mismatch": 0}
            with __import__("zipfile").ZipFile(archive) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    ar["members"] += 1
                    ar["bytes"] += info.file_size
                    rel = pathlib.PurePosixPath(info.filename)
                    local = RAW.joinpath(*rel.parts)
                    is_video = info.filename.lower().endswith(".mp4")
                    h = hashlib.sha256()
                    target = tmp / "current.mp4" if is_video else None
                    with zf.open(info) as src, (target.open("wb") if target else open(pathlib.Path(os.devnull), "wb")) as dst:  # type: ignore[name-defined]
                        while block := src.read(CHUNK):
                            h.update(block)
                            if target:
                                dst.write(block)
                    digest = h.hexdigest()
                    if is_video:
                        ar["videos"] += 1
                        ar["video_bytes"] += info.file_size
                        channel = rel.parts[-3].replace("observation.images.", "") if dataset == "EgoDemo" else rel.stem
                        record_dir = RAW / dataset / rel.parts[1]
                        probe = probe_video(target)
                        expected = expected_frames(record_dir, dataset, channel)
                        row = {
                            "dataset": dataset,
                            "member": info.filename,
                            "bytes": info.file_size,
                            "sha256": digest,
                            "expected_frames": expected,
                            **probe,
                        }
                        video_rows.append(row)
                        if not probe.get("open"):
                            ar["video_open_errors"] += 1
                            result["errors"].append(f"video open: {info.filename}")
                        elif not all(x["ok"] for x in probe["decoded_samples"]):
                            ar["video_sample_decode_errors"] += 1
                            result["warnings"].append(f"sample decode: {info.filename}")
                        if probe.get("frames") != expected:
                            ar["frame_count_mismatch"] += 1
                            result["warnings"].append(
                                f"frames {probe.get('frames')} != table {expected}: {info.filename}"
                            )
                        if target:
                            target.unlink()
                    else:
                        ar["nonvideo"] += 1
                        ar["nonvideo_bytes"] += info.file_size
                        if not local.exists():
                            ar["sha256_mismatch"] += 1
                            result["errors"].append(f"missing extracted file: {info.filename}")
                            continue
                        if sha256_file(local) != digest:
                            ar["sha256_mismatch"] += 1
                            result["errors"].append(f"sha256 mismatch: {info.filename}")
                            continue
                        try:
                            suffix = local.suffix.lower()
                            if suffix == ".csv":
                                frame = pd.read_csv(local, low_memory=False)
                                if len(frame.columns) == 0:
                                    raise ValueError("zero columns")
                            elif suffix == ".json":
                                json.loads(local.read_text(encoding="utf-8"))
                            elif suffix == ".parquet":
                                pf = pq.ParquetFile(local)
                                if pf.metadata.num_rows <= 0 or len(pf.schema) == 0:
                                    raise ValueError("empty parquet")
                            else:
                                raise ValueError(f"unexpected suffix {suffix}")
                        except Exception as exc:
                            ar["parse_errors"] += 1
                            result["errors"].append(f"parse {info.filename}: {exc}")
                        if local.name == "file-000.parquet" and "/data/" in local.as_posix():
                            payload_hashes[digest].append(info.filename)
                        if local.name in ("pose_left_hand.csv", "pose_right_hand.csv"):
                            payload_hashes[digest].append(info.filename)
                    print(f"  {ar['members']:3d} files | videos {ar['videos']:3d} | errors {len(result['errors'])}", flush=True) if ar["members"] % 50 == 0 else None
            result["archives"][dataset] = ar
            totals.update(ar)

    fps = [v["fps"] for v in video_rows if v.get("open")]
    resolutions = collections.Counter((v["width"], v["height"]) for v in video_rows if v.get("open"))
    result["summary"] = {
        "zip_members": totals["members"],
        "zip_bytes": totals["bytes"],
        "nonvideo_files": totals["nonvideo"],
        "nonvideo_bytes": totals["nonvideo_bytes"],
        "video_files": totals["videos"],
        "video_bytes": totals["video_bytes"],
        "video_total_frames": sum(v.get("frames", 0) for v in video_rows),
        "video_total_duration_s": sum(v.get("duration_s") or 0.0 for v in video_rows),
        "video_fps_values": sorted({round(x, 6) for x in fps}),
        "video_resolutions": {f"{w}x{h}": n for (w, h), n in resolutions.items()},
        "all_video_samples_decoded": all(
            v.get("open") and all(x["ok"] for x in v["decoded_samples"]) for v in video_rows
        ),
        "all_video_frame_counts_match_tables": totals["frame_count_mismatch"] == 0,
        "duplicate_main_numeric_payloads": [v for v in payload_hashes.values() if len(v) > 1],
        "elapsed_s": round(time.time() - started, 2),
    }
    result["errors_count"] = len(result["errors"])
    result["warnings_count"] = len(result["warnings"])
    result["verdict"] = "PASS" if not result["errors"] else "FAIL"
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    detail = OUT.with_name("video_audit.json")
    detail.write_text(json.dumps(video_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=1), flush=True)
    print(f"errors={len(result['errors'])} warnings={len(result['warnings'])}", flush=True)
    print(f"wrote {OUT} and {detail}", flush=True)
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())