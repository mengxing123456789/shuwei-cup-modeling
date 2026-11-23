#!/usr/bin/env python
"""\u626b\u672c\u76ee\u5f55\uff0c\u7981\u6b62\u51fa\u73b0\u6307\u5411\u83b7\u5956\u8bba\u6587/\u4f18\u79c0\u8bba\u6587\u7684\u8def\u5f84\u6216\u884c\u4e3a\uff08\u7ec3\u4e60\u8d5b\u7528\uff09\u3002

\u7528\u6cd5\uff1a
    python code/check_no_peek.py [\u76ee\u5f55]        # \u9ed8\u8ba4\u672c\u6587\u4ef6\u7684\u4e0a\u4e00\u7ea7
\u8d1f\u5bf9\u7167\uff08\u5fc5\u987b\u5148\u505a\u4e00\u6b21\uff09\uff1a
    \u5728\u672c\u76ee\u5f55\u968f\u4fbf\u5199\u4e00\u4e2a .py\uff0c\u91cc\u9762\u653e\u4e00\u884c src = r"...\\_award_text\\x.txt"
    -> \u5fc5\u987b FAIL \u5e76\u6307\u51fa\u884c\u53f7\uff1b\u5220\u6389\u540e\u5fc5\u987b PASS\u3002
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# \u8def\u5f84\u8bcd\uff1a\u51fa\u73b0\u5373\u8bf4\u660e\u5f15\u7528\u4e86\u7981\u533a\u8bed\u6599
PATH_WORDS = ["_award_text", "award_pdfs", "_award_outline", "APMCM2025_C",
              "allpapers", "excellent", "prize_lists", "\u4f18\u79c0\u8bba\u6587", "\u4e00\u7b49\u5956\u8bba\u6587"]
# \u884c\u4e3a\u8bcd\uff1a\u51fa\u73b0\u5373\u8bf4\u660e\u5728\u63cf\u8ff0"\u6284\u54ea\u7bc7"
# \u884c\u4e3a\u8bcd\u53ea\u6536"\u6307\u5411\u67d0\u4e2a\u83b7\u5956\u7b54\u6848"\u7684\u77ed\u8bed\u3002\u88f8\u7684"\u7167\u6284"\u4f1a\u547d\u4e2d"\u522b\u7167\u6284\u952e\u540d"\u8fd9\u7c7b\u6b63\u5e38\u53e5\u5b50\uff08P11 \u5b9e\u6d4b\uff09\u3002
ACT_WORDS = ["\u83b7\u5956\u8bba\u6587\u600e\u4e48", "\u53c2\u8003\u4e00\u7b49\u5956", "\u7167\u6284\u4e00\u7b49\u5956", "\u7167\u6284\u83b7\u5956", "\u4eff\u5199\u4e00\u7b49\u5956", "copy the award"]
EXT = {".py", ".md", ".tex", ".json", ".txt", ".log", ".csv", ".m"}
SKIP = {"problem", "data", "refs", "annex_A", "review", ".git", "__pycache__"}
# \u76ee\u5f55\u7ea7\u7981\u533a\uff1arefs/award_text \u662f\u4e00\u7b49\u5956\u6b63\u6587\uff0c\u7ec3\u4e60\u8d5b\u91cc\u51fa\u73b0\u5c31\u7b49\u4e8e\u628a\u7b54\u6848\u653e\u5728\u4e86\u65c1\u8fb9\u3002
# \u53ea\u5728\u6587\u4ef6\u7ea7\u626b\u4f1a\u6f0f\u6389\u5b83\uff08refs \u672c\u8eab\u8981\u8df3\u8fc7\uff0c\u56e0\u4e3a official_standard.json \u5c31\u5728\u90a3\u513f\uff09\u3002
DIR_BAN = ["refs/award_text", "award_text"]
# \u8fd9\u4e9b\u6587\u4ef6**\u672c\u6765\u5c31\u8981\u5199\u51fa\u7981\u533a\u8def\u5f84**\uff08\u5426\u5219\u6ca1\u6cd5\u544a\u8bc9\u4eba\u54ea\u4e9b\u4e0d\u80fd\u78b0\uff09\u3002\u5224\u636e\u82e5\u626b\u81ea\u5df1\u5fc5\u7136 FAIL\uff0c
# \u89c4\u5219\u6587\u6863\u4e0e\u5224\u636e\u672c\u8eab\u5fc5\u987b\u8c41\u514d\uff0c\u5426\u5219\u8d1f\u5bf9\u7167\u6c38\u8fdc\u505a\u4e0d\u51fa\u6765\uff08P11 \u5b9e\u6d4b\uff1a\u8c41\u514d\u524d 8 \u547d\u4e2d\uff09\u3002
EXEMPT = {"NO_PEEK.md", "code/check_no_peek.py"}

PAT = re.compile("|".join(map(re.escape, PATH_WORDS)), re.I)
ACT = re.compile("|".join(map(re.escape, ACT_WORDS)), re.I)


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for bad in DIR_BAN:
        d = root / bad
        if d.exists() and d.is_dir():
            hits.append(f"{bad}/ (directory: \u4e00\u7b49\u5956\u6b63\u6587\u5728\u8fd9\u91cc\uff0c\u7ec3\u4e60\u8d5b\u5fc5\u987b\u5220\u9664)")
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXT:
            continue
        rel = p.relative_to(root).as_posix()
        if set(p.relative_to(root).parts) & SKIP or rel in EXEMPT:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if PAT.search(line) or ACT.search(line):
                    hits.append(f"{p.relative_to(root)}:{i}")
        except OSError:
            continue
    return hits


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    hits = scan(root)
    for h in hits:
        print("FAIL", h)
    print(f"scanned {root}  forbidden hits {len(hits)}")
    print("VERDICT:", "PASS" if not hits else "FAIL")
    return 0 if not hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
