"""把 data_profile.json 汇总成报告用的表：质量、手部几何、区间。

只读 data/data_profile.json，不重读原始 CSV（那一步在 profile_data.py）。
复现：python code\deep_stats.py
"""

import json
import pathlib

import numpy as np

WS = pathlib.Path(__file__).resolve().parents[1]
PROFILE = WS / "data" / "data_profile.json"
OUT = WS / "data" / "deep_stats.json"


def main() -> int:
    d = json.loads(PROFILE.read_text(encoding="utf-8"))
    recs = d["records"]
    out = {
        "inventory": {},
        "quality": {},
        "hand": {},
        "segments": d["tasks"]["segments"],
        "occlusion": d["occlusion"],
    }

    for ds in ("EgoDemo", "EgoPro", "EgoStandard"):
        demo = ds == "EgoDemo"
        rs = [r for r in recs if (r["kind"] == "demo" if demo else r.get("dataset") == ds)]
        frames = sum(r["rows"] for r in rs) if demo else sum(r["rows"]["left"] for r in rs)
        bad = sum(r["bad"]["bad_any"] for r in rs) if demo else sum(r["bad"]["bad_frames"] for r in rs)
        rates = [(r["bad"]["ratio_any"] if demo else r["bad"]["ratio"]) for r in rs]
        reasons: dict[str, int] = {}
        for r in rs:
            for k, v in (r["bad"].get("reasons") or {}).items():
                reasons[k] = reasons.get(k, 0) + v
        out["inventory"][ds] = {
            "records": len(rs),
            "frames": frames,
            "envs": len({r["environment_id"] for r in rs}),
            "wrist_video": sum(1 for r in rs if r.get("has_wrist_video")),
        }
        out["quality"][ds] = {
            "frames": frames,
            "bad_frames": bad,
            "bad_rate": round(bad / frames, 6),
            "reasons": reasons,
            "rec_bad_median": round(float(np.median(rates)), 6),
            "rec_bad_max": round(float(max(rates)), 6),
        }
        spans, speeds, jumps, nanf = [], [], 0, []
        for r in rs:
            for side in ("left", "right"):
                s = (r.get("hand") or {}).get(side)
                if not s:
                    continue
                spans.append(s["centroid_span_m"])
                nanf.append(s["nan_keypoint_frame_frac"])
                speeds.append(s["speed_m_per_s"]["median"])
                jumps += s.get("jump_gt_0p2m", 0)
        sp = np.array(spans, dtype=float).reshape(len(spans), 3)
        out["hand"][ds] = {
            "samples": len(spans),
            "centroid_span_median_m": [round(float(x), 3) for x in sp.mean(axis=0)],
            "centroid_span_p95_m": [round(float(x), 3) for x in np.percentile(sp, 95, axis=0)],
            "speed_median_mps": round(float(np.median(speeds)), 4),
            "jumps_gt_0p2m": int(jumps),
            "nan_keypoint_frac_max": float(max(nanf) if nanf else 0.0),
        }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT}  {OUT.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())