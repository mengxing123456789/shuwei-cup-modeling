"""语料索引 CLI：建索引、查近邻、按年份题号枚举。

    python E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\corpus_index.py --build
    python ... --query "主动减振 离心作动器" --top 5
    python ... --query-file problem/problem.txt          # 拿新题面当查询词（最常用）
    python ... --year 2023 --problem B --kind paper --list
    python ... --stats
    python ... --show <id>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mmkit import corpus as C      # noqa: E402

KINDS = ["", "problem", "paper", "data", "appendix"]
KIND_CN = {"problem": "题面", "paper": "论文", "data": "数据", "appendix": "附录"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="历年真题/获奖论文语料索引")
    ap.add_argument("--build", action="store_true", help="重建索引")
    ap.add_argument("--root", action="append", metavar="DIR", help="语料根目录（可多次）")
    ap.add_argument("--query", "-q", default="", help="关键词查询")
    ap.add_argument("--query-file", metavar="FILE", help="用文件内容当查询词（题面）")
    ap.add_argument("--year", default="", help="限定年份，如 2023")
    ap.add_argument("--problem", default="", help="限定题号，如 B")
    ap.add_argument("--kind", default="", choices=KINDS, help="题面/论文/数据/附录")
    ap.add_argument("--top", type=int, default=8, help="返回条数")
    ap.add_argument("--list", action="store_true", help="清单模式：只给 --year/--problem/--kind 枚举")
    ap.add_argument("--show", metavar="ID", help="看某条正文头 2000 字")
    ap.add_argument("--stats", action="store_true", help="统计")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.build:
        roots = [Path(r) for r in args.root] if args.root else None
        print(f"[建索引] roots={[str(r) for r in (roots or [C.corpus_root()])]}")
        obj = C.build(roots, verbose=args.verbose)
        p = C.save(obj)
        print(f"[完成] {obj['count']} 条（去重 {obj['deduped']}）→ {p}")
        print(C.stats(obj))

    obj = C.load()
    if not obj.get("count"):
        print("[空] 还没有索引。先跑 --build")
        return 2

    if args.stats:
        print(C.stats(obj))
        return 0

    if args.show:
        hit = next((r for r in obj["records"] if r["id"] == args.show), None)
        if not hit:
            print(f"[未命中] {args.show}")
            return 2
        print(f"{hit['year']} {hit['problem']} {hit['kind']} {hit['title']}")
        print(hit["file"])
        print()
        print(hit["head"][:2000])
        return 0

    text = args.query
    if args.query_file:
        fp = Path(args.query_file)
        if not fp.exists():
            print(f"[FAIL] 查询文件不存在：{fp}")
            return 2
        text = fp.read_text(encoding="utf-8", errors="replace")[:2000]
        print(f"[查近邻] 用 {fp.name} 的前 2000 字当查询")

    if not text:
        rows = [r for r in obj["records"]
                if (not args.year or r["year"] == args.year)
                and (not args.problem or r["problem"] == args.problem.upper())
                and (not args.kind or r["kind"] == args.kind)]
        rows.sort(key=lambda r: (r["year"], r["kind"], r["problem"]))
        print(f"[清单] {len(rows)} 条")
        for r in rows[:200]:
            print(f"  {r['year']} {r['problem'] or '-'} "
                  f"{KIND_CN.get(r['kind'], r['kind'])} {r['title']}\n    {r['file']}")
        return 0

    hits = C.query(obj, text, year=args.year, problem=args.problem,
                   kind=args.kind or None, top=args.top)
    print(f"[结果] {len(hits)} 条")
    for h in hits:
        print(f"\n{h['year']} {h['problem'] or '-'} {KIND_CN.get(h['kind'], h['kind'])} "
              f"score={h.get('score', 0):.2f} {h['title']}")
        print(f"  {h['file']}")
        snip = h.get("snippet") or C.snippet(h, text)
        if snip:
            print(f"  …{snip}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())