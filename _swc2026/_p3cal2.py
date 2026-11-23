import json, os, collections

D = r'E:\数学建模\_swc2026\SWC2026_C\data'
d = json.load(open(os.path.join(D, 'p3_scheduling.json'), encoding='utf-8'))
s = [e for e in d['summary'] if e.get('alpha') is not None]
maps = [(0.75, 0.5), (1.0, 0.0), (1.0, 0.5), (1.0, 1.0), (1.5, 0.5)]
tab = {}
for e in s:
    tab[(e['case'], e['policy'], round(e['alpha'], 3), round(e['beta'], 3))] = e['weighted_on_time_rate']

for case in ('S1', 'S2', 'S3'):
    print('==' + case)
    print('  %-9s %s' % ('mapping', ' '.join('%10s' % p for p in ('edf', 'slack', 'voi', 'oracle'))))
    dv = []
    for a, b in maps:
        row = []
        for p in ('edf', 'slack', 'voi', 'oracle'):
            k = (case, p, round(a, 3), round(b, 3))
            row.append('%10.4f' % tab[k] if k in tab else '%10s' % '-')
        if (case, 'voi', a, b) in tab and (case, 'slack', a, b) in tab:
            dv.append(tab[(case, 'voi', a, b)] - tab[(case, 'slack', a, b)])
        print('  %-9s %s' % ('%.2f/%.2f' % (a, b), ' '.join(row)))
    if dv:
        print('  voi - slack : n=%d mean=%+.4f min=%+.4f max=%+.4f  neg=%d/%d'
              % (len(dv), sum(dv) / len(dv), min(dv), max(dv), sum(1 for x in dv if x < 0), len(dv)))

print()
# oracle gap on nominal
for case in ('S1', 'S2', 'S3'):
    o = tab[(case, 'oracle', 1.0, 0.5)]
    sl = tab[(case, 'slack', 1.0, 0.5)]
    ed = tab[(case, 'edf', 1.0, 0.5)]
    print('%s nominal: oracle=%.4f slack=%.4f edf=%.4f | oracle-slack=%+.4f  slack-edf=%+.4f'
          % (case, o, sl, ed, o - sl, sl - ed))