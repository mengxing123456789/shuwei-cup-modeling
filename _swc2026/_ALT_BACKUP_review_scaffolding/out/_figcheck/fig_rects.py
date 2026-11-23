# -*- coding: utf-8 -*-
"""Recover the plotted geometry (bar rects, data-point markers, axis frame) from the
five figure PDFs, then test the specific misuse claims numerically:

  A. equal-spacing of an ordered numeric axis   (fig1 panel a: 0.2/0.5/2.0/5.0 s)
  B. truncated value axis                       (fig4: y from 9, data 9.87..12.81)
  C. area-vs-length in nested bars              (fig2: AUC outer / F1 inner)
  D. coincident series                          (fig3: Kalman vs hold at L=1.0)
  E. presence of error-bar primitives           (all five)

Run:  python out\_figcheck\fig_rects.py
"""
import sys, pathlib, json
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
base = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')


def rects(pdf):
    doc = fitz.open(pdf)
    pg = doc[0]
    out = []
    for d in pg.get_drawings():
        for it in d['items']:
            if it[0] == 're':
                r = it[1]
                out.append(dict(kind='rect', x0=round(r.x0, 2), y0=round(r.y0, 2),
                                x1=round(r.x1, 2), y1=round(r.y1, 2),
                                w=round(r.width, 2), h=round(r.height, 2),
                                fill=d.get('fill'), stroke=d.get('color')))
            elif it[0] == 'l':
                p1, p2 = it[1], it[2]
                out.append(dict(kind='line', x0=round(p1.x, 2), y0=round(p1.y, 2),
                                x1=round(p2.x, 2), y1=round(p2.y, 2),
                                w=round(abs(p2.x - p1.x), 2), h=round(abs(p2.y - p1.y), 2),
                                fill=d.get('fill'), stroke=d.get('color')))
            elif it[0] == 'c':
                out.append(dict(kind='curve', fill=d.get('fill'), stroke=d.get('color')))
    doc.close()
    return out


print('#' * 78)
print('# E. error-bar primitives: a whisker is a line/rect thin in x and 2..40 pt long in y')
for p in sorted(base.glob('*.pdf')):
    rs = rects(p)
    vlines = [r for r in rs if r['kind'] == 'line' and r['w'] <= 0.6 and 2 <= r['h'] <= 40]
    hlines = [r for r in rs if r['kind'] == 'line' and r['h'] <= 0.6 and 2 <= r['w'] <= 40]
    vrects = [r for r in rs if r['kind'] == 'rect' and r['w'] <= 1.6 and 2 <= r['h'] <= 40]
    print('%-26s items=%3d  whisker_like_vlines=%d  hlines=%d  vrects=%d'
          % (p.name, len(rs), len(vlines), len(hlines), len(vrects)))

print()
print('#' * 78)
print('# A. fig1 panel (a): x centres of the 4 tolerance groups vs the stated tolerances')
rs = rects(base / 'fig1_p1_agreement.pdf')
bars = [r for r in rs if r['kind'] == 'rect' and r['h'] > 20 and r['w'] < 30]
bars.sort(key=lambda r: (r['x0']))
print('  bars (x0,y0,w,h):')
for r in bars:
    print('   ', r['x0'], r['y0'], r['w'], r['h'], r['fill'])
# group centres
cent = sorted({round((r['x0'] + r['x1']) / 2, 1) for r in bars})
print('  distinct bar centres:', cent)
if len(cent) >= 4:
    gaps = [round(cent[i + 1] - cent[i], 2) for i in range(len(cent) - 1)]
    print('  adjacent gaps:', gaps)
    print('  equally spaced on the page?', max(gaps) - min(gaps) < 0.5)
    tol = [0.2, 0.5, 2.0, 5.0]
    print('  tolerance values  :', tol)
    print('  real numeric gaps :', [round(tol[i + 1] - tol[i], 2) for i in range(3)])
    print('  gap ratio numeric / page:', [round((tol[i+1]-tol[i]) / gaps[i], 3) for i in range(min(3, len(gaps)))])

print()
print('#' * 78)
print('# B. fig4: value-axis range vs data-point vertical spread')
rs = rects(base / 'fig4_p2_voi.pdf')
doc = fitz.open(base / 'fig4_p2_voi.pdf')
pg = doc[0]
pts = []
for d in pg.get_drawings():
    for it in d['items']:
        if it[0] == 'c':  # curves used as markers
            pass
for b in pg.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            if s['text'].startswith(('A:', 'B:', 'C:')):
                pts.append((s['text'].strip(), round(s['bbox'][1], 1), round(s['bbox'][3], 1)))
print('  option label y (top,bottom):', pts)
# markers: filled circles are drawn as bezier; instead read the annotated values and the axis ticks
ticks = []
for b in pg.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            if s['text'].strip() in ('9', '10', '11', '12', '13', '14'):
                ticks.append((s['text'].strip(), round(s['bbox'][1], 1)))
print('  y tick label -> top y:', ticks)
if ticks:
    ys = [t[1] for t in ticks]
    print('  axis spans y %.1f..%.1f pt for values %s..%s' % (min(ys), max(ys), ticks[0][0], ticks[-1][0]))
    span_val = 14 - 9
    print('  so 1 cm = %.2f pt; the three points span 12.81-9.87 = %.2f cm = %.1f pt'
          % ((max(ys) - min(ys)) / span_val, 12.81 - 9.87, (12.81 - 9.87) * (max(ys) - min(ys)) / span_val))
    print('  fraction of the axis height used by the data range: %.2f'
          % ((12.81 - 9.87) / span_val))
doc.close()

print()
print('#' * 78)
print('# C. fig2: nested bars -> length encodes the value, but AREA does not')
rs = rects(base / 'fig2_p1_reliability.pdf')
bb = [r for r in rs if r['kind'] == 'rect' and r['w'] > 5 and r['h'] > 5]
bb.sort(key=lambda r: (r['y0'], r['x0']))
for r in bb:
    print('   x0=%6.2f w=%6.2f h=%6.2f  fill=%s' % (r['x0'], r['w'], r['h'], r['fill']))
outer = [r for r in bb if r['h'] > 12]
inner = [r for r in bb if r['h'] <= 12]
print('  outer (AUC) bars:', [(r['w'], r['h']) for r in outer])
print('  inner (F1) bars :', [(r['w'], r['h']) for r in inner])
if outer and inner:
    print('  inner/outer width ratio = %.4f  (constant => inner length is on the same x scale)'
          % (inner[0]['w'] / outer[0]['w']))
    print('  but inner/outer AREA ratio for AUC .914 / F1 .61: %.4f'
          % ((0.61039 * inner[0]['w'] * inner[0]['h']) / (0.91367 * outer[0]['w'] * outer[0]['h'])))
    print('  the reader who reads area gets F1/AUC = %.4f, not F1 = 0.61'
          % (0.61039 / 0.91367))
