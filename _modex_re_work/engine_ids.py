import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_modex_re_work\zlib\workflow_engine_z1.txt'
t = open(p, encoding='utf-8', errors='replace').read()

# all dash-joined lowercase tokens that look like skill ids
cand = set(re.findall(r'\b(?:comp|paper|survey|dev|course|humanities|copyright|patent|idea|novelty|research|experiment|assets|auto|nature|thesis|literature|editor|ablation|analyze|comm)-[a-z0-9]+(?:-[a-z0-9]+)*\b', t))
print('candidate ids', len(cand))
for c in sorted(cand):
    print('  ', c, t.count(c))
