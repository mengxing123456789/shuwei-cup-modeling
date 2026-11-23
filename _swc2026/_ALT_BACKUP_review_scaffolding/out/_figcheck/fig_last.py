# -*- coding: utf-8 -*-
"""Last three tests for 07-figures.md.

D1  fig0: the four box colours and whether the two "cross-question links" exist as arrows.
D2  fig2: does the value axis run past the metric's own maximum (1.0)?
D3  every figure: CJK glyphs (C7 forbids Chinese in the chart) and whether each
    figure states its own units / sample size in the artwork.

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\fig_last.py
"""
import sys, pathlib, re
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
FIG = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')

print('=' * 78)
print('D1  fig0: boxes, their fills, and every long connector')
doc = fitz.open(FIG / 'fig0_framework.pdf')
pg = doc[0]
boxes, conns = [], []
for d in pg.get_drawings():
    for it in d['items']:
        if it[0] == 're':
            r = it[1]
            if r.width > 40 and r.height > 20:
                boxes.append((round(r.x0, 1), round(r.y0, 1), round(r.width, 1), round(r.height, 1),
                              tuple(round(c, 3) for c in d['fill']) if d['fill'] else None))
        elif it[0] == 'l':
            a, b = it[1], it[2]
            L = ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
            if L > 8:
                conns.append((round(a.x, 1), round(a.y, 1), round(b.x, 1), round(b.y, 1), round(L, 1)))
print('  boxes (%d):' % len(boxes))
for b in sorted(boxes, key=lambda z: (z[1], z[0])):
    print('    x=%6.1f y=%6.1f w=%6.1f h=%6.1f fill=%s' % b)
print('  connectors longer than 8 pt (%d):' % len(conns))
for c in sorted(conns, key=lambda z: (z[1], z[0])):
    dx, dy = c[2] - c[0], c[3] - c[1]
    kind = 'horizontal' if abs(dy) < 1.5 else ('vertical' if abs(dx) < 1.5 else 'diagonal')
    print('    (%6.1f,%6.1f)->(%6.1f,%6.1f) len=%5.1f %s' % (c[0], c[1], c[2], c[3], c[4], kind))
print('  -> any connector whose endpoints lie between the Q1 box and the Q2/Q3 boxes')
print('     vertically (same x range, y span > 20 pt) would be the caption\'s link arrow.')
doc.close()

print()
print('=' * 78)
print('D2  fig2: value-axis extent vs the metric maximum 1.0')
doc = fitz.open(FIG / 'fig2_p1_reliability.pdf')
pg = doc[0]
tick = {}
frame = None
for d in pg.get_drawings():
    for it in d['items']:
        if it[0] == 're':
            r = it[1]
            if r.width > 200 and r.height > 80:
                frame = (round(r.x0, 2), round(r.x1, 2))
for b in pg.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            t = s['text'].strip()
            if t in ('0.0', '0.2', '0.4', '0.6', '0.8', '1.0'):
                tick[t] = (s['bbox'][0] + s['bbox'][2]) / 2
print('  tick x:', {k: round(v, 2) for k, v in tick.items()})
print('  axis frame x0..x1 =', frame)
if frame and '0.0' in tick and '1.0' in tick:
    per = (tick['1.0'] - tick['0.0']) / 1.0
    right_val = (frame[1] - tick['0.0']) / per
    print('  %.2f pt per unit; the frame extends to value %.3f' % (per, right_val))
    print('  -> the axis is drawn %.0f%% past the largest possible value of the metric.'
          % (100 * (right_val - 1.0)))
doc.close()

print()
print('=' * 78)
print('D3  CJK in the figures (C7) and self-explanation inventory')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]')
for p in sorted(FIG.glob('*.pdf')):
    doc = fitz.open(p)
    txt = doc[0].get_text()
    doc.close()
    n = len(CJK.findall(txt))
    has_unit = bool(re.search(r'\b(cm|cm2|cm²|%|s\)|s\b|pt)\b', txt))
    has_n = bool(re.search(r'\b(\d+\s*(windows|records|segments|annotated))\b', txt))
    print('  %-26s cjk=%d  unit-in-artwork=%-5s  n-in-artwork=%-5s'
          % (p.name, n, has_unit, has_n))
