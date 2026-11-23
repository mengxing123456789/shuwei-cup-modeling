"""语料真实性核验 CLI：把下载来的真题/附录/论文逐份核一遍，落台账。

    python E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\authenticity_check.py --build
    python ... --build --verbose            # 边核边打（大目录能看进度）
    python ... --build --only pdf,xlsx      # 只核这两类
    python ... --build --root D:\\corpus    # 换目录
    python ... --summary                    # 重看上次台账的覆盖矩阵
    python ... --list                      # 列出非 OK 的条目（要不要重下就看这个）
    python ... --show "2023…A_Problem.pdf"  # 单份详情

接口：from mmkit.authenticity import build, load, to_markdown
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mmkit import authenticity as A          # noqa: E402
from mmkit import corpus as C               # noqa: E402


def _fmt(n: int) -> str:
    return A._fmt_size(n)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="语料真实性核验")
    ap.add_argument("--build", action="store_true", help="重新核验并写台账")
    ap.add_argument("--summary", action="store_true", help="重看上次台账的统计与覆盖矩阵")
    ap.add_argument("--list", action="store_true", help="列出非 OK 条目")
    ap.add_argument("--show", metavar="SUBSTR", help="单份详情（按相对路径子串匹配）")
    ap.add_argument("--root", metavar="DIR", help="语料根目录（默认 AsterLink）")
    ap.add_argument("--only", metavar="EXT", help="只核这些扩展名，逗号分隔，如 pdf,xlsx")
    ap.add_argument("--md", metavar="PATH", help="人读台账输出路径")
    ap.add_argument("--no-md", action="store_true", help="不写 _PROVENANCE.md")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root) if args.root else C.corpus_root()

    if args.build:
        only = None
        if args.only:
            only = {x.strip().lower().lstrip(".") for x in args.only.split(",") if x.strip()}
        print(f"[核验] root={root}" + (f" only={sorted(only)}" if only else ""))
        if not root.exists():
            print(f"[FAIL] 目录不存在：{root}")
            return 2
        obj = A.build(root, only=only, verbose=args.verbose)
        jp = A.save(obj, root)
        v = obj["verdicts"]
        print(f"[完成] {obj['count']} 份  "
              + "  ".join(f"{k}={v.get(k,0)}" for k in ("OK", "SUSPECT", "BROKEN")))
        print(f"[台账] {jp}")
        if not args.no_md:
            mp = A.write_markdown(obj, Path(args.md) if args.md else None)
            print(f"[台账] {mp}")
        cov = obj.get("coverage") or {}
        if cov.get("matrix"):
            print("\n年份×题号覆盖（官方/整理）：")
            print("       " + "  ".join(A.LETTERS))
            for y in cov["years"]:
                cells = [f"{cov['matrix'][y][L] or '—':<6}" for L in A.LETTERS]
                print(f"  {y}  " + "  ".join(cells))
        bad = [e for e in obj["entries"] if e["verdict"] != "OK"]
        if bad:
            print(f"\n非 OK {len(bad)} 份（详见台账）：")
            for e in bad[:20]:
                print(f"  {e['verdict']:8s} {e['rel']} — {e['reason']}")
        return 0 if not bad else 1

    obj = A.load(root)
    if not obj.get("count"):
        print(f"[空] 还没有台账。先跑 --build（root={root}）")
        return 2

    if args.summary or not (args.list or args.show):
        v = obj.get("verdicts") or {}
        print(f"[台账] {obj['count']} 份 @ {obj['built_at']}  root={obj['root']}")
        print("  " + "  ".join(f"{k}={v.get(k,0)}" for k in ("OK", "SUSPECT", "BROKEN")))
        cov = obj.get("coverage") or {}
        if cov.get("matrix"):
            print("       " + "  ".join(A.LETTERS))
            for y in cov["years"]:
                print(f"  {y}  " + "  ".join(f"{cov['matrix'][y][L] or '—':<6}" for L in A.LETTERS))

    if args.list:
        bad = [e for e in obj["entries"] if e["verdict"] != "OK"]
        print(f"\n非 OK {len(bad)} 份：")
        for e in bad:
            print(f"  {e['verdict']:8s} {e['rel']} — {e['reason']}")

    if args.show:
        hits = [e for e in obj["entries"] if args.show.lower() in e["rel"].lower()]
        if not hits:
            print(f"[未命中] {args.show}")
            return 2
        for e in hits[:5]:
            print(f"\n{e['rel']}")
            print(f"  结论 {e['verdict']} | {e['status']} | {e['year'] or '?'} {e['problem'] or ''} "
                  f"| {_fmt(e['size'])} | {e['mtime']}")
            print(f"  sha256 {e['sha256']}")
            print(f"  依据 {e['reason']}")
            det = e.get("detail") or {}
            if det:
                print(f"  明细 {det}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())