# -*- coding: utf-8 -*-
import json
p = r'C:\modex-mh-agent\resources\app\backend\_modex-build-inputs.json'
d = json.load(open(p, encoding='utf-8'))
print(type(d), list(d)[:20] if isinstance(d, dict) else len(d))
if isinstance(d, dict):
    for k, v in d.items():
        print(k, type(v), len(v) if hasattr(v, '__len__') else '')
