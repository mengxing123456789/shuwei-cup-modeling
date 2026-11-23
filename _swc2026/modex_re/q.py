# -*- coding: utf-8 -*-
"""Query extracted strings JSON: q.py <json> <out> [regex] [--cjk]"""
import json, sys, re

def main():
    path, out = sys.argv[1], sys.argv[2]
    pattern = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
    cjk_only = '--cjk' in sys.argv
    rows = json.load(open(path, encoding='utf-8'))
    if pattern:
        rx = re.compile(pattern, re.I)
        rows = [r for r in rows if rx.search(r['s'])]
    if cjk_only:
        rows = [r for r in rows if any('\u4e00' <= ch <= '\u9fff' for ch in r['s'])]
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        for i, r in enumerate(rows):
            f.write(f"[{i}] {r['sec']}@0x{r['off']:X} len={len(r['s'])}\n{r['s']}\n---\n")
    print("matched", len(rows), "->", out)

if __name__ == '__main__': main()
