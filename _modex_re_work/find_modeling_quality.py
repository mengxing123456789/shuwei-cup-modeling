import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_modex_re_work\zlib\workflow_engine_z1.txt'
t = open(p, encoding='utf-8', errors='replace').read()

for kw in ['建模深度', 'MODELING_QUALITY', 'modeling_quality', 'PAPER_MODELING', '论文模型表达', '模型表达']:
    print('#' * 10, kw)
    for m in re.finditer(re.escape(kw), t):
        s = max(0, m.start() - 200)
        print('  @', m.start(), '|', t[s:m.start() + 260].replace('\n', ' '))
    print()
