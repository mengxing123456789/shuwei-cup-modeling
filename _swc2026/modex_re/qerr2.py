# -*- coding: utf-8 -*-
import json
p=r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json"
d=json.load(open(p,encoding="utf-8"))
print(type(d), len(d))
print(repr(d[:3]) if isinstance(d,list) else list(d.items())[:3])
