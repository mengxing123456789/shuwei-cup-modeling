# -*- coding: utf-8 -*-
"""核对 out/03-numbers.md 里的 JSON 键是否真的存在于 data/*.json。"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    txt = open(os.path.join(ROOT, "out", "03-numbers.md"), encoding="utf-8").read()
    keys = re.findall(r"`([a-z0-9_]+\.[^`]+)`", txt)
    cache, bad = {}, []
    for k in keys:
        f, path = k.split(".", 1)
        fp = os.path.join(ROOT, "data", f + ".json")
        if not os.path.exists(fp):
            bad.append((k, "<file>", "no such json"))
            continue
        if f not in cache:
            cache[f] = json.load(open(fp, encoding="utf-8"))
        o = cache[f]
        ok = True
        for part in re.split(r"\.(?![^\[]*\])", path):
            m = re.match(r"^([^\[]+)\[(\d+)\]$", part)
            try:
                o = o[m.group(1)][int(m.group(2))] if m else o[part]
            except Exception as e:
                ok = False
                bad.append((k, part, repr(e)))
                break
    print("total keys", len(keys), "bad", len(bad))
    for b in bad:
        print("BAD", b)


if __name__ == "__main__":
    main()
