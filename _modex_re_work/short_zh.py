# -*- coding: utf-8 -*-
import re, io
p = r'E:\数学建模\_modex_re_work\strings\simulated_review.txt'
rows = []
for l in open(p, encoding='utf-8'):
    parts = l.rstrip('\n').split('\t', 2)
    if len(parts) == 3 and parts[1] == 'utf8':
        rows.append((parts[0], parts[2]))
cand = [(o, s) for o, s in rows if len(s) <= 10 and re.search(r'[\u4e00-\u9fff]', s)]
out = io.open(r'E:\数学建模\_modex_re_work\short_zh_simulated.txt', 'w', encoding='utf-8')
out.write('\n'.join(f'{o}\t{s}' for o, s in cand))
out.close()
print(len(cand))
