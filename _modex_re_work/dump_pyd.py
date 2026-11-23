# -*- coding: utf-8 -*-
"""Dump CPython 3.11 code objects from a Modex .pyd (marshal at offset 16)."""
import marshal, dis, types, sys, json, io, os, re

def walk(co, out, depth=0):
    info = {
        "name": co.co_name,
        "qualname": getattr(co, "co_qualname", co.co_name),
        "file": co.co_filename,
        "line": co.co_firstlineno,
        "argcount": co.co_argcount,
        "varnames": list(co.co_varnames),
        "names": list(co.co_names),
        "consts": [],
        "children": [],
    }
    for c in co.co_consts:
        if isinstance(c, types.CodeType):
            info["children"].append(walk(c, out, depth + 1))
        elif isinstance(c, str):
            info["consts"].append(c)
    out.append(info)
    return info

def main():
    p = sys.argv[1]
    data = open(p, "rb").read()
    co = marshal.loads(data[16:])
    out = []
    tree = walk(co, out)
    if len(sys.argv) > 2 and sys.argv[2] == "--json":
        print(json.dumps(tree, ensure_ascii=False, default=str, indent=1))
        return
    # default: function index
    def show(node, prefix=""):
        print(f"{prefix}{node['qualname']}  L{node['line']}  args={node['argcount']}")
        for ch in node["children"]:
            show(ch, prefix + "  ")
    show(tree)

if __name__ == "__main__":
    main()
