# -*- coding: utf-8 -*-
import re, io
p = r'E:\数学建模\_modex_re_work\strings\simulated_review.txt'
rows = []
for l in open(p, encoding='utf-8'):
    parts = l.rstrip('\n').split('\t', 2)
    if len(parts) == 3 and parts[1] == 'utf8':
        rows.append((parts[0], parts[2]))
out = io.open(r'E:\数学建模\_modex_re_work\short_ascii_simulated.txt', 'w', encoding='utf-8')
for o, s in rows:
    if 2 <= len(s) <= 40 and re.fullmatch(r"[A-Za-z0-9_ .,:/()\[\]{}+\-=&%?!'\"<>|*#~`@$\\^]+", s):
        out.write(f'{o}\t{s}\n')
out.close()
print('done')
