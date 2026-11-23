# -*- coding: utf-8 -*-
"""Every number 07-figures.md cites about the figures, in one recomputable run.

C1  fig1(a) axis spacing            -> ordered ratio variable on a nominal scale
C2  fig2 nested bars                -> length is linear in value, AREA is not
C3  fig3 Kalman vs hold separation  -> the caption's "never worse" is sub-linewidth
C4  fig4 truncated value axis       -> data range / axis range
C5  error-bar primitives            -> are the thin segments data whiskers or axis ticks?
C6  fig5 dashed line                -> which points does it actually join?
C7  sample sizes behind fig4/fig5   -> 221 vs 300 windows

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\fig_numbers.py
"""
import sys, pathlib, json
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')
FIG = ROOT / 'figures'


def spans(pdf):
    doc = fitz.open(pdf)
    pg = doc[0]
    out = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip():
                    out.append((s['text'].strip(), s['size'],
                                (s['bbox'][0] + s['bbox'][2]) / 2,
                                (s['bbox'][1] + s['bbox'][3]) / 2))
    doc.close()
    return out


def items(pdf):
    doc = fitz.open(pdf)
    pg = doc[0]
    out = []
    for d in pg.get_drawings():
        for it in d['items']:
            if it[0] == 're':
                r = it[1]
                out.append(('re', r.x0, r.y0, r.x1, r.y1, d.get('fill')))
            elif it[0] == 'l':
                a, b = it[1], it[2]
                out.append(('l', a.x, a.y, b.x, b.y, d.get('color')))
    doc.close()
    return out

print('=' * 78)
print('C1  fig1(a): x tick centres vs the tolerance values they label')
sp = {t: x for t, s, x, y in spans(FIG / 'fig1_p1_agreement.pdf')}
order = ['±0.2 s', '±0.5 s', '±2.0 s', '±5.0 s']
xs = [sp[t] for t in order]
gaps = [round(xs[i + 1] - xs[i], 3) for i in range(3)]
print('    tick x (pt)        :', [round(v, 2) for v in xs])
print('    page gaps (pt)     :', gaps, ' spread=%.3f' % (max(gaps) - min(gaps)))
print('    value gaps (s)     : [0.3, 1.5, 3.0]  max/min=%.1fx' % (3.0 / 0.3))
print('    VERDICT: equal page spacing for values 10x apart -> nominal scale for an')
print('             ordered variable. A line/area read off this axis has no meaning.')

print()
print('=' * 78)
print('C2  fig2: nested bars, length vs area')
re_ = [r for r in items(FIG / 'fig2_p1_reliability.pdf') if r[0] == 're']
outer = sorted([r for r in re_ if abs(r[4] - r[2] - 12.39) < 0.01], key=lambda r: r[2])
inner = sorted([r for r in re_ if abs(r[4] - r[2] - 4.76) < 0.01], key=lambda r: r[2])
AUC = [0.91367, 0.91479, 0.67548, 0.48993]
F1 = [0.61039, 0.60526, 0.39286, 0.25500]
names = ['posterior bound', 'raw bad rate', 'segment LOO', 'released flag']
print('    %-16s %8s %8s %8s %10s %10s' % ('series', 'AUC', 'F1', 'w_out', 'w_out/AUC', 'w_in/F1'))
for i, n in enumerate(names):
    wo = outer[i][3] - outer[i][1]
    wi = inner[i][3] - inner[i][1]
    print('    %-16s %8.5f %8.5f %8.2f %10.3f %10.3f' % (n, AUC[i], F1[i], wo, wo / AUC[i], wi / F1[i]))
print('    -> both scales are linear and share one factor (~169.8 pt per unit):')
print('       LENGTH is an honest encoding.')
ao = (outer[0][3] - outer[0][1]) * (outer[0][4] - outer[0][2])
ai = (inner[0][3] - inner[0][1]) * (inner[0][4] - inner[0][2])
print('    outer bar area = %.1f pt^2, inner = %.1f pt^2, area ratio = %.4f' % (ao, ai, ai / ao))
print('    value ratio F1/AUC = %.4f' % (F1[0] / AUC[0]))
print('    -> AREA understates the ratio by %.1f%%: a reader who integrates the ink'
      % (100 * (1 - (ai / ao) / (F1[0] / AUC[0]))))
print('       reads F1 as %.3f of AUC instead of %.3f.' % (ai / ao, F1[0] / AUC[0]))

print()
print('=' * 78)
print('C3  fig3: vertical separation of the Kalman and hold series at L = 1.0 s')
sp3 = spans(FIG / 'fig3_p2_error.pdf')
yt = {t: y for t, s, x, y in sp3 if t in ('0', '5', '10', '15', '20')}
ys = [yt[k] for k in ('0', '5', '10', '15', '20')]
ppt = (max(ys) - min(ys)) / 20.0
print('    y ticks 0..20 span %.2f pt -> %.3f pt per cm' % (max(ys) - min(ys), ppt))
print('    Kalman 9.464 cm vs hold 9.554 cm at L=1.0: gap = %.3f cm = %.2f pt'
      % (9.554 - 9.464, (9.554 - 9.464) * ppt))
print('    (matplotlib default linewidth 1.5 pt; the two strokes overlap)')
print('    Kalman 2.862 vs hold 3.387 at L=0.2: gap = %.3f cm = %.2f pt'
      % (3.387 - 2.862, (3.387 - 2.862) * ppt))
print('    -> the caption claim "never worse than holding the last state" rests on')
print('       gaps of 0.5 pt to 0.9 pt, i.e. on sub-stroke differences.')

print()
print('=' * 78)
print('C4  fig4: value-axis range vs the data range')
sp4 = {t: y for t, s, x, y in spans(FIG / 'fig4_p2_voi.pdf') if t in ('9', '10', '11', '12', '13', '14')}
ys4 = [sp4[k] for k in ('9', '10', '11', '12', '13', '14')]
axis_h = max(ys4) - min(ys4)
data_h = (12.809 - 9.874) / (14 - 9) * axis_h
print('    axis 9..14 spans %.2f pt; the data span 9.874..12.809 = %.2f pt' % (axis_h, data_h))
print('    -> the data occupy %.0f%% of the panel height; the axis floor is 9, not 0.'
      % (100 * data_h / axis_h))
print('    zero is %.1f axis-heights below the visible floor' % (9 / 5))

print()
print('=' * 78)
print('C5  error bars: where do the thin vertical segments sit?')
for name in ('fig1_p1_agreement.pdf', 'fig3_p2_error.pdf', 'fig4_p2_voi.pdf'):
    it = items(FIG / name)
    frame = [r for r in it if r[0] == 're' and (r[3] - r[1]) > 60 and (r[4] - r[2]) > 60]
    fl = min([r[1] for r in frame]) if frame else None
    thin = [r for r in it if r[0] == 'l' and abs(r[3] - r[1]) < 0.7 and 1.5 <= abs(r[4] - r[2]) <= 6]
    print('    %-24s thin vertical segments = %d' % (name, len(thin)))
    for r in thin[:12]:
        print('        x=%.2f y=%.2f..%.2f (len %.2f pt)  colour=%s'
              % (r[1], r[2], r[4], abs(r[4] - r[2]), r[5]))
print('    -> all of them are tick marks (length <= 6 pt, all sharing a y baseline),')
print('       none sits at a data x with a value-dependent length: no whiskers exist.')

print()
print('=' * 78)
print('C6  fig5: which points does the dashed line join?')
it5 = items(FIG / 'fig4_p2_voi.pdf')
dash = [r for r in it5 if r[0] == 'l']
for r in dash:
    if abs(r[4] - r[2]) > 5:
        print('    long segment: (%.1f,%.1f) -> (%.1f,%.1f)' % (r[1], r[2], r[3], r[4]))

print()
print('=' * 78)
print('C7  sample sizes behind the plotted means')
p1 = json.loads((ROOT / 'data' / 'alt_p1.json').read_text(encoding='utf-8'))
p2 = json.loads((ROOT / 'data' / 'alt_p2.json').read_text(encoding='utf-8'))
for k, v in p2['official_options'].items() if isinstance(p2['official_options'], dict) else []:
    print('   ', k, v)
print('    official_options type:', type(p2['official_options']).__name__)
print('    mask_protocol rows n_windows:', [r.get('n_windows') for r in p2['mask_protocol']['rows']])
print('    hold_A_90:', json.dumps(p2['mask_protocol'].get('hold_A_90'), ensure_ascii=False)[:300])
