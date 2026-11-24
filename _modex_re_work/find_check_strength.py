import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_modex_re_work\zlib\workflow_intake_z1.txt'
t = open(p, encoding='utf-8', errors='replace').read()

for kw in ['校验强度', '严格', '视觉质检', 'advisory', 'polish']:
    print('#' * 10, kw)
    for m in re.finditer(re.escape(kw), t):
        s = max(0, m.start() - 260)
        print('  @', m.start(), '|', t[s:m.start() + 300].replace('\n', ' '))
    print()
