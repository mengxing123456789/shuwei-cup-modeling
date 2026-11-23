# -*- coding: utf-8 -*-
"""Q2 robustness: do the q/R doubling claims and the alpha ablation have product keys?
main.tex:291 says doubling q or R moves the mean by <0.005 cm;
main.tex:367 says <0.01 cm. Same phenomenon, two numbers.

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\p2_robust_keys.py
"""
import sys, json, pathlib

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')
d = json.load(open(R / 'data' / 'alt_p2.json', encoding='utf-8'))


def walk(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, p + '.' + k)
    elif isinstance(o, list):
        print('%-58s [list n=%d]' % (p, len(o)))
    else:
        print('%-58s %s' % (p, o))


walk(d)
print()
print('top-level keys:', list(d.keys()))
