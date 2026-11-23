# -*- coding: utf-8 -*-
"""Dump structure + strings from a compiled .pyd whose payload is marshal data at offset 16."""
import marshal, dis, sys, types, json, os

def load_code(path):
    data = open(path, 'rb').read()
    print(f"FILE {path} size={len(data)}")
    print("HEADER16:", data[:16].hex())
    try:
        code = marshal.loads(data[16:])
        print("MARSHAL OK:", type(code), getattr(code, 'co_name', None))
        return code
    except Exception as e:
        print("marshal offset16 failed:", e)
        # try other offsets
        for off in range(0, 32):
            try:
                c = marshal.loads(data[off:])
                if isinstance(c, types.CodeType):
                    print(f"MARSHAL OK at offset {off}: {c.co_name}")
                    return c
            except Exception:
                pass
        raise

def walk(code, depth=0, out=None, funcs=None):
    if out is None: out = []
    if funcs is None: funcs = []
    name = code.co_name
    funcs.append({
        "name": name,
        "qualname": getattr(code, 'co_qualname', name),
        "firstlineno": code.co_firstlineno,
        "argcount": code.co_argcount,
        "varnames": list(code.co_varnames),
        "names": list(code.co_names),
        "consts_repr": [repr(c)[:300] for c in code.co_consts if isinstance(c, (str, int, float, bytes)) and not isinstance(c, bool)],
        "nested": [],
    })
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            funcs[-1]["nested"].append(walk(c, depth+1, out, funcs))
    return funcs

def main():
    path = sys.argv[1]
    code = load_code(path)
    funcs = walk(code)
    outpath = sys.argv[2] if len(sys.argv) > 2 else path + ".dump.json"
    with open(outpath, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(funcs, f, ensure_ascii=False, indent=2)
    print("WROTE", outpath, os.path.getsize(outpath))

if __name__ == '__main__':
    main()
