# -*- coding: utf-8 -*-
"""Extract per-figure geometry from the five figure PDFs so the 07-figures.md
verdicts are recomputable without reading alt_figures.py.

For each figure: every text span (size, bbox, string), plus the drawing primitives
(rects/lines) reduced to a summary: how many rects, their width/height ranges,
whether any rect is thin enough to be an error bar, and the axis frame bbox.

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\fig_geometry.py
"""
import sys, pathlib, json
import fitz

sys.stdout.reconfigure(encoding='utf-8')
base = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')
out = {}
for p in sorted(base.glob('*.pdf')):
    doc = fitz.open(p)
    pg = doc[0]
    spans = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text']
                if t.strip():
                    spans.append((round(s['size'], 2), [round(v, 1) for v in s['bbox']], t))
    drawings = pg.get_drawings()
    rects, thin_v, thin_h = [], 0, 0
    for d in drawings:
        r = d['rect']
        rects.append((round(r.x0, 1), round(r.y0, 1), round(r.width, 1), round(r.height, 1)))
        # error bar = very thin in one dimension and short in the other
        if 0 < r.width <= 1.6 and 2 < r.height <= 40:
            thin_v += 1
        if 0 < r.height <= 1.6 and 2 < r.width <= 40:
            thin_h += 1
    xs = [s[1][0] for s in spans]
    ys = [s[1][1] for s in spans]
    out[p.name] = dict(
        page=(round(pg.rect.width, 1), round(pg.rect.height, 1)),
        n_spans=len(spans),
        sizes=sorted({s[0] for s in spans}),
        n_drawings=len(drawings),
        n_rects=len(rects),
        thin_vertical=thin_v, thin_horizontal=thin_h,
        text_bbox=[round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
        texts=[(s[0], s[2]) for s in spans],
    )
    doc.close()

for k, v in out.items():
    print('=' * 70)
    print(k, 'page', v['page'], 'spans', v['n_spans'], 'sizes', v['sizes'])
    print('  drawings', v['n_drawings'], 'rects', v['n_rects'],
          'thin_vertical', v['thin_vertical'], 'thin_horizontal', v['thin_horizontal'])
    print('  text bbox', v['text_bbox'])
    print('  strings:')
    for size, t in v['texts']:
        print('    %5.2f  %s' % (size, t))
pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\out\_figcheck\fig_geometry.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
