# -*- coding: utf-8 -*-
"""fig0 part 2: the 48 curves. Are they arrowheads, the diagonal connectors, or the
caption's two cross-question link arrows? Answer by listing every curve's bbox.

Run:  python out\_figcheck\fig0_curves.py
"""
import sys, pathlib
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
FIG = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')
doc = fitz.open(FIG / 'fig0_framework.pdf')
pg = doc[0]

cur = []
for d in pg.get_drawings():
    for it in d['items']:
        if it[0] == 'c':
            pts = it[1:]
            xs = [p.x for p in pts]
            ys = [p.y for p in pts]
            cur.append((round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1),
                        round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1),
                        tuple(round(c, 3) for c in d['fill']) if d.get('fill') else None))
doc.close()

print('curves: %d' % len(cur))
big = [c for c in cur if c[4] > 6 or c[5] > 6]
small = [c for c in cur if c[4] <= 6 and c[5] <= 6]
print('  small (arrowhead-sized, <=6 pt each way): %d' % len(small))
print('  larger (connector or arc): %d' % len(big))
for c in sorted(big, key=lambda z: (z[1], z[0])):
    print('    x %6.1f..%6.1f  y %6.1f..%6.1f  w=%5.1f h=%5.1f fill=%s' % c)

print()
print('Interpretation test: a cross-question link arrow from the Q1 box (x 207..286,')
print('y 33..57) down to the Q3 box (x 207..286, y 97..121) would have a bbox with')
print('w>5 and h>20 in that x band. Count them:')
n = [c for c in big if 200 <= c[0] <= 290 and c[5] > 20]
print('  such curves: %d' % len(n))
for c in n:
    print('    ', c)
