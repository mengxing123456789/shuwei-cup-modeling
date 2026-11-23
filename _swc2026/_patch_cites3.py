import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

subs = [
    ('\\paragraph{Formalisation.} The observed state is the dominant-wrist position',
     '\\paragraph{Formalisation.} The setting is a partially observed decision problem in the\nsense of \\cite{kaelbling1998}: the state is estimated from what the camera saw, and what\nit costs to see more is part of the decision. The observed state is the dominant-wrist\nposition'),
    ('Tool & DeepSeek Harness (command-line coding agent), DeepSeek & agent loop, file editing, shell execution',
     'Tool & DeepSeek Harness (command-line coding agent), DeepSeek \\cite{deepseek} & agent loop, file editing, shell execution'),
]

for old, new in subs:
    n = t.count(old)
    print('count=%d anchor=%r' % (n, old[:50]))
    assert n == 1, 'anchor not unique: ' + old[:60]
    t = t.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('cites =', t.count('\\cite{'))