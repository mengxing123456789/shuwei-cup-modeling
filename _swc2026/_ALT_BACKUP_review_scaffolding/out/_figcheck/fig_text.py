# -*- coding: utf-8 -*-
"""Exact text drawn inside fig3 (error) and fig4 (voi), plus the baselines table
that fig3 plots, so every printed glyph can be traced to a JSON key.

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\fig_text.py
"""
import sys, json, pathlib
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')

for f in ('fig3_p2_error.pdf', 'fig4_p2_voi.pdf'):
    doc = fitz.open(R / 'figures' / f)
    pg = doc[0]
    print('=' * 70)
    print(f, 'page %.1f x %.1f' % (pg.rect.width, pg.rect.height))
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip():
                    print('  %-38s %5.2f pt  x %6.1f y %6.1f'
                          % (repr(s['text'].strip()), s['size'], s['bbox'][0], s['bbox'][1]))
    doc.close()

print()
print('=' * 70)
d = json.load(open(R / 'data' / 'alt_p2.json', encoding='utf-8'))
print('mask_protocol.baselines (what fig3 should plot):')
for b in d['mask_protocol']['baselines']:
    print('  ', json.dumps(b, ensure_ascii=False))
