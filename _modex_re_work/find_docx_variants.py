import io, sys, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

paths = [
    r'E:\数学建模\_modex_re_work\zlib\workflow_engine_z1.txt',
    r'E:\数学建模\_modex_re_work\zlib\workflow_intake_z1.txt',
    r'E:\数学建模\_modex_re_work\zlib\chat_executor_z1.txt',
    r'E:\数学建模\_modex_re_work\zlib2\skill_runtime_policy_87008.txt',
]
ids = ['comp-paper-zh-docx', 'comp-paper-en-docx', 'paper-write-docx', 'paper-write-zh-docx',
       'paper-write-nature-docx', 'comp-paper-huawei-zh-docx', 'editor-agent',
       'humanities-write-latex', 'paper-figure-html', 'ablation-planner', 'analyze-results',
       'comm-lit-review', 'docx-export', 'auto-review-loop']
for p in paths:
    t = open(p, encoding='utf-8', errors='replace').read()
    print('=' * 12, os.path.basename(p), len(t))
    for i in ids:
        n = t.count(i)
        if n:
            print('  ', i, n)
            # show a window around first occurrence
            k = t.find(i)
            print('      ...', t[max(0, k - 90):k + 90].replace('\n', ' '))
