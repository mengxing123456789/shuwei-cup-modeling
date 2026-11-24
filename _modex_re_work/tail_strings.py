# -*- coding: utf-8 -*-
import io
p = r'E:\数学建模\_modex_re_work\strings\simulated_review.txt'
rows = []
for l in open(p, encoding='utf-8'):
    parts = l.rstrip('\n').split('\t', 2)
    if len(parts) == 3 and parts[1] == 'utf8':
        try:
            off = int(parts[0], 16)
        except ValueError:
            continue
        rows.append((off, parts[2]))
out = io.open(r'E:\数学建模\_modex_re_work\simulated_tail.txt', 'w', encoding='utf-8')
for off, s in rows:
    if off >= 0x00101b00:
        out.write(f'{off:08x}\t{s}\n')
out.close()
print('done')
