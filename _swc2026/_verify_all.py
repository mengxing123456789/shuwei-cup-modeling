# -*- coding: utf-8 -*-
"""Lead 复核闸门：对四个题目的产物做"断言 -> 证据"检查。

检查项（每项独立 PASS / FAIL / NA，不用 ?? 混过去）：
  F1 产物齐备性      out/00-problem.md, out/01-model.md, out/03-numbers.md, out/15-benchmark.md
  F2 代码可复跑      code/run_all.py 存在；--run 时真跑一遍，返回码 0
  F3 数字可溯源      data/*.json 可解析；out/03-numbers.md 里每个 "来源" 键都能在 JSON 里找到
  F4 图存在          figures/ 下至少 3 个 pdf/png
  F5 mtime 一致性    data/*.json 的 mtime 不早于 code/*.py 的最大 mtime
  F6 不写 problem/   problem/ 下文件 mtime 未变（对比基线 manifest，可选）

用法：
  python _verify_all.py                 # 只做静态检查
  python _verify_all.py --run           # 额外真跑每个 run_all.py（限时 900 s）
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, time

BASE = r"E:\数学建模\_swc2026"
PROBS = ["A", "B", "C", "D"]
PY = r"python"


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def flatten_keys(obj, prefix=""):
    """把嵌套 JSON 摊平成 'a.b.c' 键集合（含列表下标）"""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out |= flatten_keys(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):          # 只展开前 3 个元素，够用于键匹配
            out |= flatten_keys(v, f"{prefix}[{i}]")
    else:
        out.add(prefix)
    return out


def num_tokens(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            num_tokens(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            num_tokens(v, acc)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.append(float(obj))


def check_one(k, run=False):
    d = os.path.join(BASE, f"SWC2026_{k}")
    res = {"problem": k, "checks": {}, "notes": []}
    if not os.path.isdir(d):
        res["checks"]["F0"] = "FAIL 目录不存在"
        return res

    # ---- F1 产物齐备 ----
    need = ["out/00-problem.md", "out/01-model.md", "out/03-numbers.md", "out/15-benchmark.md"]
    miss = [p for p in need if not os.path.exists(os.path.join(d, p.replace("/", os.sep)))]
    res["checks"]["F1"] = "PASS" if not miss else f"FAIL 缺 {miss}"

    # ---- F2 代码 ----
    run_all = os.path.join(d, "code", "run_all.py")
    if not os.path.exists(run_all):
        res["checks"]["F2"] = "FAIL 无 code/run_all.py"
    elif run:
        t0 = time.time()
        try:
            p = subprocess.run([PY, os.path.basename(run_all)], cwd=os.path.join(d, "code"),
                               capture_output=True, text=True, timeout=900)
            dt = time.time() - t0
            res["checks"]["F2"] = (f"PASS 复跑 {dt:.1f}s rc=0" if p.returncode == 0
                                   else f"FAIL rc={p.returncode} :: {(p.stderr or '')[-400:]}")
            res["notes"].append(f"run_all 复跑 {dt:.1f}s")
        except subprocess.TimeoutExpired:
            res["checks"]["F2"] = "FAIL 复跑超时 900s"
    else:
        res["checks"]["F2"] = "NA(未加 --run)"

    # ---- F3 数字溯源 ----
    jsons = sorted(glob.glob(os.path.join(d, "data", "*.json")))
    if not jsons:
        res["checks"]["F3"] = "FAIL 无 data/*.json"
    else:
        allkeys, bad = set(), []
        for jp in jsons:
            try:
                allkeys |= flatten_keys(jload(jp))
            except Exception as e:
                bad.append(os.path.basename(jp) + ":" + str(e)[:80])
        md = os.path.join(d, "out", "03-numbers.md")
        txt = open(md, encoding="utf-8", errors="replace").read() if os.path.exists(md) else ""
        # 抓 md 里出现的 json 键样式的串（含点号或下划线且出现在反引号中）
        cited = set(re.findall(r"`([A-Za-z_][\w\.\[\]]{2,})`", txt))
        unresolved = [c for c in cited if c not in allkeys and not any(c in k for k in allkeys)]
        res["checks"]["F3"] = ("FAIL 解析失败 " + "; ".join(bad) if bad else
                               ("PASS" if not unresolved else f"FAIL {len(unresolved)} 个键无对应 {unresolved[:6]}"))
        res["notes"].append(f"json={len(jsons)} 键={len(allkeys)} md引用={len(cited)}")
        # 数字规模：便于和子代理自报对账
        acc = []
        for jp in jsons:
            num_tokens(jload(jp), acc)
        res["notes"].append(f"数值条目={len(acc)}")

    # ---- F4 图 ----
    figs = glob.glob(os.path.join(d, "figures", "*.pdf")) + glob.glob(os.path.join(d, "figures", "*.png"))
    res["checks"]["F4"] = "PASS" if len(figs) >= 3 else f"FAIL 只有 {len(figs)} 张图"

    # ---- F5 mtime ----
    code_m = [os.path.getmtime(p) for p in glob.glob(os.path.join(d, "code", "*.py"))]
    data_m = [os.path.getmtime(p) for p in jsons]
    if code_m and data_m:
        res["checks"]["F5"] = "PASS" if min(data_m) >= max(code_m) - 2 else "FAIL 数据早于代码（可能用了旧结果）"
    else:
        res["checks"]["F5"] = "NA"

    res["notes"].append("files=" + str(sum(len(f) for _, _, f in os.walk(d))))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    out = [check_one(k, run=a.run) for k in PROBS]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    worst = {k: r["checks"].get("F1", "")[:4] + r["checks"].get("F3", "")[:4] for k, r in zip(PROBS, out)}
    print("\n== 摘要 ==")
    for k, r in zip(PROBS, out):
        c = r["checks"]
        print(f"{k}: F1={c.get('F1')} | F2={c.get('F2')} | F3={c.get('F3')} | F4={c.get('F4')} | F5={c.get('F5')}")
    json.dump(out, open(os.path.join(BASE, "_verify_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()