"""八波派单一条命令跑完：`run_squad.py <论文目录> [--waves 0-7] [--dry]`

为什么需要：RUNBOOK §3.2 原来要人抄一段 here-string 再改名字，抄错一个字符就
静默走偏。这里把它做成脚本，并把"每波结束先验收再下一波"写死在循环里。

取舍：
- 派单逻辑全走 `mmkit.crew`，这里只负责"波次推进"与"打印"，不重复实现。
- `--dry` 只打印每波要派谁、依赖什么，不碰 API —— 用于检查 brief 有没有漏。
- 任何一波没落地就**停下**并返回非零，不自动跳过：跳过会让下游读不到上游产物，
  整条链的结论都作废。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mmkit import crew  # noqa: E402


def parse_waves(spec: str) -> list[int]:
    if not spec:
        return list(range(len(crew.WAVES)))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    bad = [w for w in out if w < 0 or w >= len(crew.WAVES)]
    if bad:
        raise SystemExit(f"wave {bad} out of range 0..{len(crew.WAVES) - 1}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="按 crew.WAVES 的十波派单（主队 18 人）")
    ap.add_argument("paper", help="论文目录（brief 里的工作区也用它）")
    ap.add_argument("--waves", default="", help="如 0-2 或 0,1,7；缺省全部")
    ap.add_argument("--timeout", type=int, default=2400, help="每波等待秒数")
    ap.add_argument("--dry", action="store_true", help="只打印不派单")
    args = ap.parse_args(argv)

    ws = paper = Path(args.paper)
    if not ws.exists():
        raise SystemExit(f"目录不存在: {ws}")
    if not (ws / "main.tex").exists():
        print(f"WARN: {ws} 里没有 main.tex，先跑 new_paper.py")

    waves = parse_waves(args.waves)
    print(f"工作区: {ws}")
    print(f"波次: {waves}   成员数: {sum(len(crew.WAVES[w]) for w in waves)}")
    if args.dry:
        for w in waves:
            for name in crew.WAVES[w]:
                deps = crew.DEPENDS.get(name, [])
                print(f"  W{w} {name:<8} deps={deps}  -> {crew.OUTPUT_OF[name]}")
        return 0

    # 一次把 13 份 brief 按本题路径重打；成员名字与路径都写死在里面
    for name, status in crew.push_briefs(ws, paper):
        print(f"  brief {name:<8} {status}")
        if status.startswith(("MISMATCH", "NO-BODY")):
            print("FATAL: brief 更新失败，派单会去读旧路径。先修 crew.py 再跑。")
            return 2

    for w in waves:
        members = crew.WAVES[w]
        print(f"\n=== W{w} 派 {len(members)} 人: {members}")
        t0 = time.time()
        before = crew.stamp(ws, members)  # 先记空壳时刻，再派单
        sent = crew.dispatch(ws, paper, members)
        for name, sid in sent.items():
            print(f"  {name:<8} {sid}")
        st = crew.wait(ws, members, timeout_s=args.timeout, since=before)
        missing = [n for n, ok in st.items() if not ok]
        print(f"W{w} 用时 {int(time.time() - t0)}s  landed={sum(st.values())}/{len(st)}")
        # 逐个报发生了什么：delivered / blocked / failed / missing
        # BLOCKED 与 FAIL 是契约内的正常回报，不是"没干活"，但它们要人看
        stop = False
        for name in members:
            o = crew.outcome(ws, name)
            print(f"  {name:<8} {o}")
            if o == "blocked":
                p = ws / crew.OUTPUT_OF[name]
                first = [l for l in p.read_text(encoding="utf-8").splitlines() if "BLOCKED:" in l]
                print(f"    {first[0].strip() if first else 'BLOCKED'}")
                stop = True
        if missing:
            # 报清楚"为什么不算交付"，否则只会看到"未交付"三个字，不知道为什么
            for name in missing:
                why = crew._too_small(ws, name)
                p = ws / crew.OUTPUT_OF[name]
                print(f"  {name}: 文件={'有' if p.exists() else '无'} 原因={why or '未在派单后写入'}")
            print(f"STOP: W{w} 未交付 {missing}")
            print("按 RUNBOOK §3.3 复验已有产物；缺的那份要么补派，要么先修上游。")
            return 1
        if stop:
            print(f"STOP: W{w} 有成员报 BLOCKED —— 上游产物缺失或不可用，先补上游再往下派。")
            return 1
    print("\n全部波次落地。接着跑 RUNBOOK §5 的九道门。")
    return 0


if __name__ == "__main__":
    sys.exit(main())