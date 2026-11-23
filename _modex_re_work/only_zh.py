# -*- coding: utf-8 -*-
import io, re, sys
p = sys.argv[1]
out = sys.argv[2]
rows = []
for l in io.open(p, encoding='utf-8'):
    parts = l.rstrip('\n').split('\t', 2)
    if len(parts) == 3 and parts[1] == 'utf8' and re.search(r'[\u4e00-\u9fff]', parts[2]):
        rows.append((parts[0], parts[2]))
io.open(out, 'w', encoding='utf-8').write('\n'.join(f'{o}\t{s}' for o, s in rows))
print(len(rows))
