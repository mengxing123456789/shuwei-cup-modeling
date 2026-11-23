import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_modex_re_work\strings\paper_modeling_quality.txt'
t = open(p, encoding='utf-8', errors='replace').read()
seen = set()
for l in t.splitlines():
    s = l.strip()
    if len(s) < 6 or len(s) > 200:
        continue
    if re.search(r'(MIN_|MAX_|_MIN|_MAX|THRESH|LIMIT|RATIO|>=|<=|min_|max_)', s):
        if s not in seen:
            seen.add(s)
            print(s[:190])
print('--- total', len(seen))
