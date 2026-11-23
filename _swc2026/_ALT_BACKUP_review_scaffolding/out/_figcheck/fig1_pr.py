# -*- coding: utf-8 -*-
"""fig1(a): decompose the micro-F1 into precision and recall.

micro F1 = 2*TP / (n_pred + n_true), with n_true = 280 fixed and n_pred differing
between the two detectors (399 vs 276). So the same F1 means different things for
the two methods. Recover TP, then precision and recall, for all four tolerances.

Run:  python out\_figcheck\fig1_pr.py
"""
import sys, json, pathlib
import pymupdf as fitz

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')
d = json.load(open(R / 'data' / 'alt_p1.json', encoding='utf-8'))

print('=' * 78)
print('fig1(a) decomposition: micro-F1 -> TP -> precision/recall')
print('%-6s %-10s %6s %6s %8s %8s %8s %8s' %
      ('tol', 'method', 'n_pred', 'n_true', 'F1', 'TP', 'precision', 'recall'))
rows = []
for tol in ('0.2', '0.5', '2.0', '5.0'):
    for meth, node in (('BOCPD', d['bocpd']['f1']['tol_' + tol]),
                       ('Thresh', d['baseline']['f1']['tol_' + tol])):
        f1 = node['micro_f1']
        n_pred, n_true = node['n_pred'], node['n_true']
        tp = f1 * (n_pred + n_true) / 2.0
        prec = tp / n_pred
        rec = tp / n_true
        rows.append((tol, meth, n_pred, n_true, f1, tp, prec, rec))
        print('%-6s %-10s %6d %6d %8.5f %8.1f %8.4f %8.4f'
              % (tol, meth, n_pred, n_true, f1, tp, prec, rec))

print()
print('per-tolerance comparison:')
for tol in ('0.2', '0.5', '2.0', '5.0'):
    b = [r for r in rows if r[0] == tol and r[1] == 'BOCPD'][0]
    t = [r for r in rows if r[0] == tol and r[1] == 'Thresh'][0]
    print('  tol=%-4s  F1: BOCPD %.4f vs Thresh %.4f  (dF1=%+.4f, BOCPD %s)'
          % (tol, b[4], t[4], b[4] - t[4], 'wins' if b[4] > t[4] else 'loses'))
    print('            recall: %.4f vs %.4f (d=%+.4f)   precision: %.4f vs %.4f (d=%+.4f)'
          % (b[7], t[7], b[7] - t[7], b[6], t[6], b[6] - t[6]))

print()
print('Reading: BOCPD recall is HIGHER than the baseline at every tolerance,')
print('including 0.2 s where the caption says the baseline "is better". The F1')
print('loss at strict tolerance is entirely a precision loss caused by 399 vs 276')
print('predictions. The figure plots F1 only, so it cannot show which happened.')

print()
print('=' * 78)
print('fig1 and fig2 text inventory')
for f in ('fig1_p1_agreement.pdf', 'fig2_p1_reliability.pdf'):
    doc = fitz.open(R / 'figures' / f)
    pg = doc[0]
    print('--', f)
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip():
                    print('   %-44s %5.2f pt  x %6.1f y %6.1f'
                          % (repr(s['text'].strip()), s['size'], s['bbox'][0], s['bbox'][1]))
    doc.close()
