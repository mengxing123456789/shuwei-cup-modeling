# -*- coding: utf-8 -*-
"""fig0 anatomy, done properly: list every drawing item type, recover the boxes as
filled quads/curves, and test whether the caption's two "cross-question links" are
drawn as arrows or only written as a footnote line of text.

Run:  python out\_figcheck\fig0_anatomy.py
"""
import sys, pathlib, collections
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
FIG = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')
doc = fitz.open(FIG / 'fig0_framework.pdf')
pg = doc[0]

kinds = collections.Counter()
shapes = []
for d in pg.get_drawings():
    for it in d['items']:
        kinds[it[0]] += 1
print('item kinds:', dict(kinds))

# collect every closed shape with a fill, as its bbox
filled = []
for d in pg.get_drawings():
    if d.get('fill') is None:
        continue
    r = d['rect']
    if r.width > 3 and r.height > 3:
        filled.append((round(r.x0, 1), round(r.y0, 1), round(r.width, 1), round(r.height, 1),
                       tuple(round(c, 3) for c in d['fill']), d.get('type')))
print()
print('filled shapes with area (%d), sorted by y then x:' % len(filled))
for f in sorted(filled, key=lambda z: (z[1], z[0])):
    print('   x=%6.1f y=%6.1f w=%6.1f h=%6.1f fill=%s type=%s' % f)

print()
print('distinct fills used for the boxes:')
c = collections.Counter(f[4] for f in filled if f[2] > 40 and f[3] > 15)
for k, n in c.items():
    print('   %s  x%d boxes' % (k, n))
print('   -> a reader must guess what the four colours mean: no legend, and the')
print('      caption names no colour.')

# arrowheads: small filled triangles (w or h between 2 and 12 pt)
print()
print('small filled shapes 2..14 pt (candidate arrowheads):')
heads = [f for f in filled if 2 <= f[2] <= 14 and 2 <= f[3] <= 14]
for f in sorted(heads, key=lambda z: (z[1], z[0])):
    print('   x=%6.1f y=%6.1f w=%5.1f h=%5.1f' % f[:4])
print('   n=%d' % len(heads))

# where could a cross-question arrow be? between col3 (x 210..283) and col3 rows
print()
print('geometry of the third column (the Q boxes) and its rows:')
rows = sorted({(round(f[1]), round(f[3])) for f in filled if 205 <= f[0] <= 215 and f[2] > 60})
print('   Q column boxes (y0,h):', rows)
print('   vertical gaps between consecutive Q boxes:',
      [rows[i + 1][0] - (rows[i][0] + rows[i][1]) for i in range(len(rows) - 1)] if len(rows) > 1 else 'n/a')
print('   -> if the gap between two Q boxes is under ~4 pt there is no room for an arrow;')
print('      a link that the caption calls a structural relation is then only text.')
doc.close()
