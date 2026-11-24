import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pj = json.load(open(r'E:\数学建模\.agents\skills\paper-kit\pipelines.json', encoding='utf-8'))
pipe_ids = set()
for tpl, spec in pj.items():
    for st in spec.get('steps', []):
        pipe_ids.add(st['skill_name'])
print('templates', len(pj), 'pipeline skill ids', len(pipe_ids))

# 43 ids extracted manually from zlib2/skill_runtime_policy_87008.txt (Cython concatenates
# string literals, so regex extraction over the raw blob cannot recover them reliably).
policy_ids = set("""ablation-planner analyze-results assets-inventory comm-lit-review comp-code
comp-compile-en comp-compile-zh comp-modeling comp-paper-en comp-paper-en-docx
comp-paper-huawei-zh comp-paper-huawei-zh-docx comp-paper-zh comp-paper-zh-docx
comp-prob-analysis comp-stats-analysis comp-stats-topic course-paper course-plan
course-report course-report-plan editor-agent experiment-bridge humanities-plan
humanities-write humanities-write-latex literature-review nature-figure paper-analysis
paper-compile paper-compile-zh paper-figure paper-figure-drawio paper-figure-html
paper-plan paper-plan-zh paper-write paper-write-docx paper-write-nature
paper-write-nature-docx paper-write-zh paper-write-zh-docx thesis-proposal""".split())
print('policy ids', len(policy_ids))

union = pipe_ids | policy_ids
print('union', len(union))
print('policy-only', sorted(policy_ids - pipe_ids))
print('pipeline-only', sorted(pipe_ids - policy_ids))

from collections import Counter
def grp(i):
    if i.startswith('comp-'): return 'A comp'
    if i.startswith(('paper-', 'nature-')): return 'B paper'
    if i.startswith('survey-'): return 'C survey'
    if i.startswith('dev-'): return 'D dev'
    if i.startswith(('copyright-', 'patent-')): return 'E ip'
    if i.startswith(('idea-', 'research-', 'experiment-', 'auto-review', 'assets-', 'ablation-', 'analyze-', 'comm-')): return 'F academic'
    if i.startswith(('course-', 'humanities-', 'thesis-', 'literature-')): return 'G edu'
    if i == 'editor-agent': return 'H internal'
    if i == 'docx-export': return 'I export'
    return 'Z other:' + i
c = Counter(grp(i) for i in union)
for k in sorted(c): print(k, c[k])
print('sum', sum(c.values()))

# report check: which ids are named in the report's group tables
rep = open(r'E:\数学建模\_swc2026\46-Modex逆向-技能与质检层.md', encoding='utf-8').read()
absent = sorted(i for i in union if i not in rep)
print('ids absent from report:', len(absent), absent)
