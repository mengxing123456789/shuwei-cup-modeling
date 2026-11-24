import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_modex_re_work\zlib\workflow_engine_z1.txt'
t = open(p, encoding='utf-8', errors='replace').read()
print('LEN', len(t))
for a, b, tag in [
    (71630, 75800, 'DOCX_TRAPS'),
    (7681, 9200, 'MCM_AI_FIG'),
    (84556, 85560, 'KEY_TABOO'),
]:
    print('=' * 30, tag, a, b)
    print(t[a:b])
    print()
