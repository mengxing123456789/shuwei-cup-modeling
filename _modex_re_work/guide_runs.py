import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

for p in [r'E:\数学建模\_modex_re_work\zlib3\writing_guide_25770.txt',
          r'E:\数学建模\_modex_re_work\zlib3\writing_profile_303e0.txt']:
    raw = open(p, 'rb').read()
    print('#' * 20, p, len(raw))
    # UTF-8 CJK runs
    txt = raw.decode('utf-8', 'replace')
    runs = re.findall(r'[\u4e00-\u9fff][\u4e00-\u9fff\u3000-\u303f\uff00-\uffef0-9A-Za-z，。、；：（）“”《》\-—…·\s]{6,}', txt)
    print('utf8 cjk runs:', len(runs))
    for r in runs[:40]:
        print('  *', r.strip()[:160])
    print()
