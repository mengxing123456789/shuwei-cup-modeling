"""派评审小队（13 人，三波），并在派单**之前**生成口径基线 review/00-metrics.md。

为什么要有 00-metrics.md：2018A 第一轮 8 个审读员各自重跑同一组命令，报告里对同一份 PDF
给出 68 页 / 72 页两种口径；而其中 3 条"废稿级"其实是我一边改它一边评它造成的。
把机器判据先跑成一份带时间戳与 sha256 的文件，审读员就有唯一基线，冲突时能一眼看出谁在什么时候看的什么。

用法（论文目录可省略，默认 find_paper()）：
    D:\\Python\\python.exe run_review.py metrics [论文目录]
    D:\\Python\\python.exe run_review.py wave0   [论文目录]     # 9 人并发 + 00-metrics.md
    D:\\Python\\python.exe run_review.py wave1   [论文目录]     # 总编收口
    D:\\Python\\python.exe run_review.py status  [论文目录]
    D:\\Python\\python.exe run_review.py team                  # 只建成/核对 13 人名册
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from mmkit import crew, paths, review_crew as RC  # noqa: E402

WS = Path(r"E:\数学建模")
PY_NUMPY = Path(sys.executable)                                   # 跑本脚本的解释器；不再写死 D:\Python
PY_MUPDF = Path(r"E:\Mini\envs\mathmodel\python.exe")           # pymupdf/openpyxl

# 派单前要跑的机器判据：(标签, 解释器, 参数)。
# 脚本一律用**绝对路径**：cwd 是论文目录，相对路径会 exit=2 "can't open file"（实测踩过，
# 而且那一行还会被当成"判据不可用"写进基线文件里，比没有更糟）。
TOOLS = [
    ("review_check", PY_MUPDF, [str(SCRIPTS / "review_check.py"), "{paper}"]),
    ("gauntlet_check", PY_NUMPY, [str(SCRIPTS / "gauntlet_check.py"), "{paper}"]),
    ("figfont", PY_MUPDF, ["-m", "mmkit.figfont", "{paper}/main.pdf"]),
    ("verify_numbers", PY_NUMPY, None),      # 在论文目录里跑 code/verify_numbers.py
    ("freshness", PY_NUMPY, ["-m", "mmkit.freshness", "{paper}"]),
]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()[:32]


def _stamp(p: Path) -> str:
    if not p.exists():
        return "MISSING"
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
    return f"{ts}  {p.stat().st_size:>9} B  sha256:{_sha256(p)}"


def _run(label: str, interp: Path, args, cwd: Path) -> tuple[int, str]:
    if args is None:
        script = cwd / "code" / "verify_numbers.py"
        if not script.exists():
            return 127, "(no code/verify_numbers.py)"
        args = [str(script)]
    env = dict(**__import__("os").environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(SCRIPTS) + (";" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        r = subprocess.run([str(interp), *map(str, args)], cwd=str(cwd), capture_output=True,
                           timeout=1800, env=env)
    except Exception as exc:                                     # noqa: BLE001
        return 1, f"<{type(exc).__name__}: {exc}>"
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    return r.returncode, out.strip()


def metrics(paper: Path) -> Path:
    """跑四条机器判据 + 新鲜度，写 <paper>/review/00-metrics.md。返回路径。"""
    out_path = paper / "review" / "00-metrics.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    L.append("# 00 口径基线（由 run_review.py metrics 自动生成，不是审读员写的）\n")
    L.append(f"生成时刻 {time.strftime('%Y-%m-%d %H:%M:%S')}　论文目录 `{paper}`\n")
    L.append("## 0. 被测件的身份（先看这一节，再读任何报告）\n")
    L.append("| 文件 | mtime / 大小 / 摘要 |")
    L.append("|---|---|")
    for rel in ("main.pdf", "main.tex", "A1899001.pdf"):
        p = paper / rel
        if p.exists():
            L.append(f"| `{rel}` | {_stamp(p)} |")
    data = sorted((paper / "data").glob("*.json")) if (paper / "data").exists() else []
    if data:
        newest = max(data, key=lambda q: q.stat().st_mtime)
        oldest = min(data, key=lambda q: q.stat().st_mtime)
        L.append(f"| `data/*.json` ({len(data)} 个) | "
                 f"最早 {time.strftime('%H:%M:%S', time.localtime(oldest.stat().st_mtime))}"
                 f" → 最新 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(newest.stat().st_mtime))} |")
        pdf = paper / "main.pdf"
        if pdf.exists() and newest.stat().st_mtime > pdf.stat().st_mtime + 60:
            lag = (newest.stat().st_mtime - pdf.stat().st_mtime) / 3600.0
            L.append(f"\n> **WARNING：数据层比 main.pdf 新 {lag:.2f} 小时 —— 论文字里的数字可能已被重跑覆盖。**\n"
                     f"> 先 `xelatex main.tex` 两次再评，或明确按\"落后 N 小时\"写进报告（R-V11）。\n")
    L.append("\n## 1. 机器判据原始输出\n")
    for label, interp, args in TOOLS:
        args = [a.replace("{paper}", str(paper)) for a in args] if args else None
        code, out = _run(label, interp, args, paper)
        L.append(f"### {label}　exit={code}　（{interp.name}）\n")
        L.append("```")
        L.append(out[-6000:] if out else "(no output)")
        L.append("```\n")
    L.append("## 2. 怎么用这份文件\n")
    L.append("- 你的结论若与这里的数字不同，并列两个数并写清\"我在何时对哪个文件重跑\"，"
             "不许只写你自己的（R-V11：报告是快照）。")
    L.append("- 这里的 PASS 只覆盖它能自动判的那几条；它**不**等于论文没问题 —— "
             "`verify_numbers.py` 绿着也照样可以有数字过期（R-V09）。")
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out_path}  ({out_path.stat().st_size} B)")
    return out_path


def _paper(argv: list[str]) -> Path:
    if len(argv) > 2:
        return Path(argv[2]).resolve()
    return paths.find_paper().root


def _sess_file(paper: Path) -> Path:
    return paper / "review" / "sessions.json"


def wave(paper: Path, idx: int, overrides: dict[str, str] | None = None) -> int:
    crew.use_review_mode(crew.REVIEW_TEAM_ID)
    metrics(paper)
    names = list(RC.WAVES[idx])
    ov = dict(overrides or {})
    # 第一轮实测：这两个成员的会话跑满 3600 s、200+ 工具、零字节落盘，全是探索。
    # 只加一句"第一个动作先落盘骨架"，任务颗粒度不动。
    if idx == 0:
        for n in ("模型与检验审读", "数据与代码审读", "创新性评估", "数字对账员"):
            if n in names and n not in ov:
                ov[n] = (f"第一个动作必须是写出 {paper / RC.OUTPUT_OF[n]} 的骨架（标题 + 空表格）并保存，"
                         "之后再逐节整文件覆盖。不许先探索再写。\n\n")
    got = crew.dispatch(WS, paper, names, ov)
    f = _sess_file(paper)
    f.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    prev.update(got)
    f.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, s in got.items():
        print(f"{n}\t{s}")
    print(f"\n{len(got)} dispatched -> {f}")
    return 0


def member(paper: Path, who: str) -> int:
    """只派一个成员（补派/复验用）。例：member 数字对账员 <dir>"""
    crew.use_review_mode(crew.REVIEW_TEAM_ID)
    if not (paper / "review" / "00-metrics.md").exists():
        metrics(paper)
    if who not in RC.OUTPUT_OF:
        print(f"unknown member {who}; known: {', '.join(RC.OUTPUT_OF)}")
        return 2
    got = crew.dispatch(WS, paper, [who])
    f = _sess_file(paper)
    f.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    prev.update(got)
    f.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, s in got.items():
        print(f"{n}\t{s}")
    return 0


def status(paper: Path) -> int:
    crew.use_review_mode(crew.REVIEW_TEAM_ID)
    print(f"metrics: {(paper / 'review' / '00-metrics.md')}")
    for name in [n for n, _ in RC.MEMBERS]:
        out = paper / RC.OUTPUT_OF[name]
        if out.exists():
            print(f"{name}\t{out.stat().st_size:>7} B\toutcome={crew.outcome(paper, name)}")
        else:
            print(f"{name}\t      -  \toutcome={crew.outcome(paper, name)}")
    return 0


def team(paper: Path, pin: bool = False) -> int:
    """建/核对 13 人名册（**连 brief 一起写**），并把 id 写进 squads/mathmodeling/review_team_id.txt。

    2026-11-12 事故：这一支原来只发 {name, permission}，upsert 把 10 个成员的 brief 全清成 0，
    UI 上显示"10 位成员 / 没有简介"，看起来像一支空队（13 人后同样适用）。现在名册与 brief 同源，且读回校验。

    工作区**默认不钉**（`pin=False`）：钉住之后每次派单都会在那个工作区的会话列表里新建一条
    "数学建模评审小队 / …"，一天就把用户自己的对话淹掉（2026-11-12 用户要求回到"未绑定（用
    宿主默认目录）"）。文件写入本来就靠绝对路径，不依赖会话落在哪个目录；要钉请显式 `--pin`。
    """
    briefs = RC.full_briefs(WS, paper)
    members = [{"name": n, "permission": p, "brief": briefs[n]} for n, p in RC.MEMBERS]
    empty = [m["name"] for m in members if not m["brief"].strip()]
    if empty:
        print(f"REFUSE: {empty} 的 brief 是空的，不写名册")
        return 2
    wid = ""
    if pin:
        wid = crew.workspace_id_for(paper) or ""
        if not wid:
            print(f"WARNING: --pin 给了但找不到 {paper} 的工作区 id，仍按未绑定处理")
    got = crew.create_team(RC.TEAM_NAME, members, description=RC.TEAM_DESCRIPTION,
                           workspace_id=wid)
    tid = got.get("teamId") or got.get("id") or ""
    print(f"team={tid} name={got.get('name')}  workspace={'pinned' if wid else 'unbound (host default)'}")
    back = crew.use_review_mode(tid) if tid else None
    listed = crew.list_members()
    zero = [m["name"] for m in listed if not m.get("brief_len")]
    print(f"members_read_back={len(listed)}  brief_len min={min((m['brief_len'] for m in listed), default=0)}  zero={zero}")
    if tid:
        f = WS / "squads" / "mathmodeling" / "review_team_id.txt"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(tid + "\n", encoding="utf-8")
        print(f"wrote {f}")
    ok = back is not False and len(listed) == len(RC.MEMBERS) and not zero
    return 0 if ok else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "team":
        argv = sys.argv[2:]
        pin = "--pin" in argv
        argv = [a for a in argv if a != "--pin"]
        return team(_paper([sys.argv[0], "x", argv[0]] if argv else [sys.argv[0]]), pin=pin)
    paper = _paper(sys.argv)
    if cmd == "metrics":
        metrics(paper)
        return 0
    if cmd == "wave0":
        return wave(paper, 0)
    if cmd == "wave1":
        return wave(paper, 1)
    if cmd == "member":
        who = sys.argv[2] if len(sys.argv) > 2 else ""
        return member(_paper([sys.argv[0], "x", sys.argv[3]] if len(sys.argv) > 3 else [sys.argv[0]]), who)
    if cmd == "status":
        return status(paper)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
