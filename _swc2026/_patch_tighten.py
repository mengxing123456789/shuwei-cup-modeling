import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

subs = [
    ('\\paragraph{Formalisation.} The setting is a partially observed decision problem in the\nsense of \\cite{kaelbling1998}: the state is estimated from what the camera saw, and what\nit costs to see more is part of the decision. The observed state is the dominant-wrist\nposition',
     '\\paragraph{Formalisation.} This is a partially observed decision problem\n\\cite{kaelbling1998}: what it costs to see more is part of the decision. The observed\nstate is the dominant-wrist position'),
    ('declares every generative tool the\nteam used. The work was carried out with one interactive coding assistant operated\nlocally through the team\'s own shell and data directories; several model routes were\nselected inside that assistant during the window, so the tool is named once and the\nroutes are recorded rather than claimed homogeneous. No other generative tool, and no\nonline service that answers questions about the data, was used: the released package\nwas never uploaded anywhere.',
     'declares every generative tool the team\nused. One interactive coding assistant, operated locally through the team\'s own shell and\ndata directories, drafted scripts and prose and ran consistency checks; several model\nroutes were selected inside it during the window, so it is cited once rather than claimed\nhomogeneous. No other generative tool ran, no online service answered questions about the\ndata, and the released package was never uploaded.'),
]

for old, new in subs:
    n = t.count(old)
    print('count=%d anchor=%r' % (n, old[:46]))
    assert n == 1, 'anchor not unique: ' + old[:60]
    t = t.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('written')