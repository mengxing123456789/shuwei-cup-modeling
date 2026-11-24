# -*- coding: utf-8 -*-
import sys, io, re
p = sys.argv[1]; out = sys.argv[2]
data = open(p,'rb').read()
res=[]
# decode whole as utf-8 ignoring errors loses offsets; slide over CJK byte patterns
pat = re.compile(rb'(?:[\xe4-\xe9][\x80-\xbf]{2}|[\x20-\x7e]){4,}')
for m in pat.finditer(data):
    b=m.group()
    try:
        s=b.decode('utf-8')
    except Exception:
        continue
    if re.search(r'[\u4e00-\u9fff]', s):
        res.append((m.start(), s))
with io.open(out,'w',encoding='utf-8') as f:
    for off,s in res:
        f.write(f'{off:08x}\t{s}\n')
print(len(res))
