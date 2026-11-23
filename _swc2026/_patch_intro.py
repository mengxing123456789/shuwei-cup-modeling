import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

subs = [
    # 1) compress the restatement of the three questions
    ('\\textbf{Part I} asks for a state and a reliability notion, a reproducible\n'
     'baseline, retention statistics, parameter uncertainty and failure cases, and it\n'
     'warns that a qualified record is a reference, not ground truth. \\textbf{Part II}\n'
     'asks how prediction error grows once observations stop, how long a prediction\n'
     'stays inside a tolerance, and when a new observation is worth requesting; it\n'
     'fixes windows, budgets, per-request costs and return delays in advance and forbids\n'
     'using returned information before its delay elapses. \\textbf{Part III} asks for a\n'
     'scheduling policy under an unknown service time with a reserved buffer, a paid\n'
     'review budget and a capacity limit, evaluated over the official seeds.',
     '\\textbf{Part I} asks for a state, a reliability notion, a reproducible baseline and\n'
     'failure cases, noting that a qualified record is a reference, not ground truth.\n'
     '\\textbf{Part II} asks how error grows once observation stops and when a new look is\n'
     'worth its cost, with windows, budgets, per-request costs and return delays fixed in\n'
     'advance and no use of information before its delay elapses. \\textbf{Part III} asks\n'
     'for a policy under an unknown service time with a reserved buffer, a paid review\n'
     'budget and a capacity limit, on the official seeds.'),
    # 2) compress the chain paragraph
    ('Our chain is deliberately thin: Part I produces a three-dimensional point and a soft reliability\n'
     'weight, Part II predicts that point and prices the next look, Part III consumes\n'
     'the price signal and the prediction-error scale but not the raw trajectory. Where\n'
     'the chain is not closed we say so in Section~\\ref{sec:eval}, rather than claiming\n'
     'an end-to-end system.',
     'The chain is thin by design: Part I gives a point and a soft weight, Part II predicts\n'
     'that point and prices the next look, Part III consumes the price and the error scale but\n'
     'not the trajectory. Where it does not close we say so in Section~\\ref{sec:eval}.'),
    # 3) compress the organisation paragraph
    ('Section~\\ref{sec:data} fixes the data conventions and the protocol.\n'
     'Sections~\\ref{sec:partone}--\\ref{sec:partthree} answer the three questions in the\n'
     'six-part form (model, solution, results, validation, discussion, summary).\n'
     'Section~\\ref{sec:limits} states the empirical decision limits of the task,\n'
     'Section~\\ref{sec:eval} collects the limitations and the reproduction commands, and\n'
     'Section~\\ref{sec:concl} concludes. Appendices hold the notation, the excerpted\n'
     'code and the command list.',
     'Section~\\ref{sec:data} fixes conventions and protocol;\n'
     'Sections~\\ref{sec:partone}--\\ref{sec:partthree} answer the three questions in the\n'
     'six-part form; Section~\\ref{sec:limits} states the empirical decision limits,\n'
     'Section~\\ref{sec:eval} the limitations and reproduction commands, and\n'
     'Section~\\ref{sec:concl} concludes. Appendices hold notation, code excerpts and the\n'
     'command list.'),
]

for old, new in subs:
    n = t.count(old)
    print('count=%d anchor=%r' % (n, old[:44]))
    assert n == 1, 'anchor not unique: ' + old[:60]
    t = t.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('written')