# -*- coding: utf-8 -*-
"""Lead 的时间线算术审计器（不重算几何，只查自洽性）。

用法：
  python _audit_timeline.py <data.json 或 目录> [...]

查什么（每条独立报 VIOLATION / OK）：
  A1 每台车的条目按 depart 升序，且上一段 reset_end <= 下一段 depart（容差 tol）
  A2 obs_end - obs_start == 5.0（观测窗固定 5 s）
  A3 slew_s == max(|pan|,|tilt|)/30（转速 30°/s，双轴同时取较长者）
  A4 obs_start == arrive + slew_s（容差 tol）
  A5 arrive - depart == travel_s（若 JSON 给了 travel_s 才查）
  A6 每个警报恰有 2 台车、且两台互不相同
  A7 警报 obs_start == max(两台车各自 obs_start)（容差 tol）
  A8 reset_end >= obs_end（回正动作存在）
  A9 P4 的 η == k/N（若同时给了 k 与 N）

设计：靠结构自动识别字段，不硬编码 schema。
  - "车辆时间线"：dict，其值都是 list，list 里的元素是 dict 且含 obs_start
  - "警报表"：dict，其值是 dict 且含 obs_start 与 vehicles/vehs（list）
"""
from __future__ import annotations

import json
import os
import sys

TOL = 2e-3
OBS_WINDOW = 5.0
SLEW_RATE = 30.0


def walk(obj, path=""):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def is_timeline(d):
    if not isinstance(d, dict) or not d:
        return False
    vals = list(d.values())
    if not all(isinstance(v, list) for v in vals):
        return False
    segs = [s for v in vals for s in v if isinstance(s, dict)]
    return bool(segs) and all("obs_start" in s for s in segs)


def is_alert_table(d):
    if not isinstance(d, dict) or not d:
        return False
    vals = list(d.values())
    if not all(isinstance(v, dict) and "obs_start" in v for v in vals):
        return False
    return any(isinstance(v.get("vehicles", v.get("vehs")), list) for v in vals)


def audit(tl, al, tag, viol, ok):
    """tl: {veh: [seg...]}  al: {alert: {...}}"""
    # ---- 车辆段自洽 ----
    for veh, segs in tl.items():
        prev = None
        for i, s in enumerate(segs):
            t = s.get("depart")
            a = s.get("arrive")
            sw = s.get("slew_s")
            o0 = s.get("obs_start")
            o1 = s.get("obs_end")
            rs = s.get("reset_end", s.get("reset", None))
            tr = s.get("travel_s", s.get("travel", None))
            key = f"{tag}:{veh}[{i}]"
            if prev is not None and t is not None:
                if t < prev - TOL:
                    viol.append(f"{key} 出发 {t} 早于上一段回正结束 {prev}")
                else:
                    ok.append(f"{key} 顺序 OK ({prev} -> {t})")
            if None not in (o0, o1) and abs((o1 - o0) - OBS_WINDOW) > TOL:
                viol.append(f"{key} 观测窗 {o1 - o0:.4f} != 5.0")
            if sw is not None:
                pan = s.get("pan_deg", s.get("pan"))
                tilt = s.get("tilt_deg", s.get("tilt"))
                if pan is not None and tilt is not None:
                    want = max(abs(pan), abs(tilt)) / SLEW_RATE
                    if abs(want - sw) > TOL:
                        viol.append(f"{key} slew {sw:.4f} != max(|{pan}|,|{tilt}|)/30 = {want:.4f}")
                    else:
                        ok.append(f"{key} slew OK {sw:.4f}")
                elif s.get("slew_axis_deg") and isinstance(s["slew_axis_deg"], dict):
                    ax = s["slew_axis_deg"]
                    want = max(abs(ax.get("pan", 0)), abs(ax.get("tilt", 0))) / SLEW_RATE
                    if abs(want - sw) > TOL:
                        viol.append(f"{key} slew {sw:.4f} != {want:.4f}")
            if None not in (a, sw, o0) and abs((a + sw) - o0) > TOL:
                viol.append(f"{key} obs_start {o0:.4f} != arrive {a:.4f} + slew {sw:.4f}")
            if None not in (t, a, tr) and abs((a - t) - tr) > TOL:
                viol.append(f"{key} arrive-depart {a - t:.4f} != travel {tr:.4f}")
            if None not in (o1, rs) and rs < o1 - TOL:
                viol.append(f"{key} reset_end {rs} 早于 obs_end {o1}")
            prev = rs if rs is not None else o1

    # ---- 警报表自洽 ----
    for alr, rec in al.items():
        vs = rec.get("vehicles") or rec.get("vehs") or []
        o0 = rec.get("obs_start")
        if len(vs) != 2:
            viol.append(f"{tag}:{alr} 车数 {len(vs)} != 2")
        if len(set(vs)) != len(vs):
            viol.append(f"{tag}:{alr} 车辆重复 {vs}")
        got = []
        for v in vs:
            for s in tl.get(v, []):
                if s.get("to_alert", s.get("alert")) == alr and s.get("obs_start") is not None:
                    got.append(s["obs_start"])
        if o0 is not None and got:
            if abs(max(got) - o0) > TOL:
                viol.append(f"{tag}:{alr} obs_start {o0:.4f} != max(两车) {max(got):.4f}")
            else:
                ok.append(f"{tag}:{alr} obs_start = max(两车) = {o0:.4f} OK")

    # ---- η ----
    for p, node in walk(al):
        if isinstance(node, dict) and {"k", "N"} <= set(node):
            k, N = node["k"], node["N"]
            if N and abs(k / N - node.get("eta", k / N)) > 1e-6:
                viol.append(f"{tag}{p} η 与 k/N 不一致")


def scan(path):
    viol, ok, found = [], [], []
    try:
        obj = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"{os.path.basename(path)} 无法解析: {e}"], [], []
    for p, node in walk(obj):
        if is_timeline(node):
            found.append(("timeline", p))
        elif is_alert_table(node):
            found.append(("alerts", p))
    # 配对：同一父节点下的 timeline 与 alerts
    tls = [p for k, p in found if k == "timeline"]
    als = [p for k, p in found if k == "alerts"]
    def get(p):
        expr = "obj" + "".join(f"[{x}]" if x.isdigit() else f"[{x!r}]" for x in _path_parts(p))
        return eval(expr, {"obj": obj})
    for tp in tls:
        par = tp.rsplit(".", 1)[0] if "." in tp else ""
        cand = [a for a in als if (a.rsplit(".", 1)[0] if "." in a else "") == par] or als
        if not cand:
            viol.append(f"{os.path.basename(path)}: 有 timeline 但没找到 alerts 表（{tp}），只能查车辆段自洽")
            audit(get(tp), {}, tp, viol, ok)
        else:
            audit(get(tp), get(cand[0]), f"{os.path.basename(path)}:{tp.rsplit('.',1)[-1]}", viol, ok)
    if not tls:
        if "q2" in os.path.basename(path) or "p2" in os.path.basename(path):
            viol.append(f"{os.path.basename(path)}: 没找到任何时间线结构（结构识别失败，需人工看 schema）")
    return viol, ok, found


def _path_parts(p):
    out, cur = [], ""
    for ch in p:
        if ch == ".":
            if cur:
                out.append(cur)
            cur = ""
        elif ch == "[":
            if cur:
                out.append(cur)
            cur = ""
        elif ch == "]":
            if cur:
                out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a)) if f.endswith(".json")]
        else:
            files.append(a)
    allv, allo = [], []
    for f in files:
        v, o, found = scan(f)
        allv += v
        allo += o
        print(f"[{os.path.basename(f)}] 结构={[k for k, _ in found]} OK={len(o)} VIOLATION={len(v)}")
        for x in v[:12]:
            print("   !!", x)
    print(f"\n== 汇总 == 文件 {len(files)} | 通过条目 {len(allo)} | 违规 {len(allv)}")
    json.dump({"violations": allv, "passed": allo},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_audit_timeline.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if allv else 0


if __name__ == "__main__":
    sys.exit(main())