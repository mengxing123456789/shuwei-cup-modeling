# -*- coding: utf-8 -*-
"""Disassemble a named code object from a .pyd/.pyc."""
import marshal, dis, types, sys

def find(co, name):
    if co.co_name == name or getattr(co, 'co_qualname', '') == name:
        return co
    for c in co.co_consts:
        if isinstance(c, types.CodeType):
            r = find(c, name)
            if r: return r
    return None

p, name = sys.argv[1], sys.argv[2]
d = open(p, 'rb').read()
co = marshal.loads(d[16:])
target = find(co, name)
if not target:
    print('NOT FOUND', name)
    sys.exit(1)
print('FILE', target.co_filename, 'LINE', target.co_firstlineno)
dis.dis(target)
