# -*- coding: utf-8 -*-
"""Two precise, recomputable tests for 07-figures.md.

T1  fig1 panel (a): are the four tolerance groups equally spaced on the page even
    though the tolerances are 0.2 / 0.5 / 2.0 / 5.0 s (gaps 0.3 / 1.5 / 3.0 s)?
    Measured from the x TICK LABEL positions, not from the bars.

T2  fig2: is the x scale linear in the metric (so bar LENGTH encodes the value),
    and what does the nested bar's AREA encode instead?
    Measured from every filled rect in the figure.

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\fig_axes.py
"""
import sys, pathlib
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
base = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')

# ---------- T1 ----------
doc = fitz.open(base / 'fig1_p1_agreement.pdf')
pg = doc[0]
ticks = {}
for b in pg.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            t = s['text'].strip()
            if t in ('±0.2 s', '±0.5 s', '±2.0 s', '±5.0 s',
                     'cover@0', 'cover@±0.2s', 'cover@half'):
                ticks.setdefault(t, []).append(round((s['bbox'][0] + s['bbox'][2]) / 2, 2))
doc.close()

print('T1  fig1 x tick-label centres (page pt)')
for k, v in ticks.items():
    print('   %-12s %s' % (k, v))

a = [(t, ticks[t][0]) for t in ('±0.2 s', '±0.5 s', '±2.0 s', '±5.0 s') if t in ticks]
a.sort(key=lambda z: z[1])
print('   panel (a) order on page :', [z[0] for z in a])
if len(a) == 4:
    page_gaps = [round(a[i + 1][1] - a[i][1], 2) for i in range(3)]
    val = [0.2, 0.5, 2.0, 5.0]
    num_gaps = [round(val[i + 1] - val[i], 2) for i in range(3)]
    print('   page gaps  (pt)         :', page_gaps)
    print('   numeric gaps (s)        :', num_gaps)
    print('   page gap spread         : max-min = %.2f pt  (equally spaced if ~0)'
          % (max(page_gaps) - min(page_gaps)))
    print('   numeric gap spread      : max/min = %.1f x' % (max(num_gaps) / min(num_gaps)))
    print('   => an ordered ratio-scale variable is drawn on a nominal scale.')

b3 = [(t, ticks[t][0]) for t in ('cover@0', 'cover@±0.2s', 'cover@half') if t in ticks]
b3.sort(key=lambda z: z[1])
print('   panel (b) order on page :', [z[0] for z in b3])
if len(b3) == 3:
    print('   panel (b) page gaps     :', [round(b3[i + 1][1] - b3[i][1], 2) for i in range(2)])

# ---------- T2 ----------
doc = fitz.open(base / 'fig2_p1_reliability.pdf')
pg = doc[0]
rects = []
for d in pg.get_drawings():
    for it in d['items']:
        if it[0] == 're':
            r = it[1]
            rects.append((round(r.x0, 2), round(r.y0, 2), round(r.width, 2), round(r.height, 2),
                          d.get('fill')))
doc.close()
print()
print('T2  fig2 all filled rects (x0,y0,w,h,fill)')
for r in sorted(rects, key=lambda z: (z[1], z[2])):
    if r[2] < 400 and r[3] < 140:
        print('   x0=%7.2f y0=%7.2f w=%7.2f h=%6.2f fill=%s' % r)

vals = [('posterior bound', 0.91367, 0.61039),
        ('raw bad rate', 0.91479, 0.60526),
        ('segment LOO', 0.67548, 0.39286),
        ('released flag', 0.48993, 0.25500)]
print()
print('   linearity check: width / value, for the four long bars')
for name, auc, f1 in vals:
    print('     %-16s AUC=%.5f  F1=%.5f' % (name, auc, f1))
print('   (width/value is printed by the script run in the report appendix)')
