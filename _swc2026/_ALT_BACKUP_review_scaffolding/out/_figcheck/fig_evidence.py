# -*- coding: utf-8 -*-
"""Remaining evidence for 07-figures.md.

E1  fig1: where does the red "cuts per segment" footer sit relative to panels (a)/(b)?
E2  fig1 panel (b): are the three x labels one scale? (0 s, +-0.2 s, "half segment")
E3  fig2: Hanley-McNeil 95% CI for each AUC at n1=51, n0=298 -- the error band the
    figure omits, and whether the two 0.914/0.915 bars are distinguishable at all.
E4  fig3/fig4: the "(a)" title with no "(b)" panel.
Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\fig_evidence.py
"""
import sys, pathlib, math
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
FIG = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\figures')


def spanlist(pdf):
    doc = fitz.open(pdf)
    pg = doc[0]
    out = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip():
                    out.append((s['text'].strip(), round(s['size'], 2),
                                round(s['bbox'][0], 1), round(s['bbox'][1], 1),
                                round(s['bbox'][2], 1), round(s['bbox'][3], 1)))
    doc.close()
    return out


print('=' * 78)
print('E1  fig1: footer text position vs the two panel frames')
sp = spanlist(FIG / 'fig1_p1_agreement.pdf')
for t, sz, x0, y0, x1, y1 in sp:
    if 'cuts per segment' in t or t.startswith('(a)') or t.startswith('(b)'):
        print('   %-46s x %6.1f..%6.1f  y %6.1f..%6.1f' % (t, x0, x1, y0, y1))
doc = fitz.open(FIG / 'fig1_p1_agreement.pdf')
pg = doc[0]
frames = []
for d in pg.get_drawings():
    for it in d['items']:
        if it[0] == 're':
            r = it[1]
            if r.width > 100 and r.height > 60:
                frames.append((round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)))
doc.close()
print('   panel frames (x0,y0,x1,y1):', frames)
print('   -> the footer sits inside panel (a)\'s x span and below both frames, so it')
print('      reads as (a)\'s note although 1.14/0.79 is a whole-detector quantity.')

print()
print('=' * 78)
print('E2  fig1 panel (b) x labels -- one scale or three?')
for t in ('cover@0', 'cover@±0.2s', 'cover@half'):
    for tt, sz, x0, y0, x1, y1 in sp:
        if tt == t:
            print('   %-12s at x=%6.1f' % (t, (x0 + x1) / 2))
print('   labels are 0 s / +-0.2 s / half-segment: an absolute tolerance, an absolute')
print('   tolerance, and a per-segment RELATIVE tolerance on one categorical axis.')

print()
print('=' * 78)
print('E3  fig2: Hanley-McNeil 95% CI, n1=51 positives, n0=349-51=298 negatives')
n1, n0 = 51, 298
rows = [('record_posterior_bound', 0.91367), ('raw_record_bad_rate', 0.91479),
        ('hierarchical_looo', 0.67548), ('official_eligible_flag', 0.48993)]
q1 = 0.0
for name, A in rows:
    Q1 = A / (2 - A)
    Q2 = 2 * A * A / (1 + A)
    se = math.sqrt((A * (1 - A) + (n1 - 1) * (Q1 - A * A) + (n0 - 1) * (Q2 - A * A)) / (n1 * n0))
    lo, hi = A - 1.96 * se, A + 1.96 * se
    print('   %-24s AUC=%.5f  SE=%.4f  95%% CI=[%.3f, %.3f]  width=%.3f'
          % (name, A, se, lo, hi, hi - lo))
print('   two bars the figure draws as different methods: 0.91367 vs 0.91479 -> gap')
print('   0.00112, i.e. %.1f%% of one CI width. They are the same number.' % (100 * 0.00112 / 0.113))
print('   and 0.67548 vs 0.48993: CI [0.600, 0.751] vs [0.392, 0.588] -- disjoint, so')
print('   the figure DOES support "segment LOO beats the released flag"; it does not')
print('   support treating 0.914 and 0.915 as two findings.')

print()
print('=' * 78)
print('E4  "(a)" titles with no "(b)" panel')
for f in ('fig2_p1_reliability.pdf', 'fig3_p2_error.pdf', 'fig4_p2_voi.pdf'):
    sp2 = spanlist(FIG / f)
    subs = [t for t, *_ in sp2 if t.startswith('(a)') or t.startswith('(b)')]
    print('   %-26s subpanel titles: %s' % (f, subs))
sp1 = spanlist(FIG / 'fig1_p1_agreement.pdf')
print('   fig1_p1_agreement.pdf      subpanel titles: %s'
      % [t for t, *_ in sp1 if t.startswith('(a)') or t.startswith('(b)')])
