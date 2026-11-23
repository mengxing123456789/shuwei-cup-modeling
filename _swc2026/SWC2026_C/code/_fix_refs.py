import pathlib
p = pathlib.Path('main.tex')
s = p.read_text(encoding='utf-8')
reps = [
    ("\\emph{Statistical\nAnalysis with Missing Data} [M]. Wiley.",
     "\\emph{Statistical\nAnalysis with Missing Data} [M]. Wiley, pp. 1--462."),
    ("\\emph{Algorithmic\nLearning in a Random World} [M]. Springer.",
     "\\emph{Algorithmic\nLearning in a Random World} [M]. Springer, pp. 1--324."),
    ("\\emph{Scheduling: Theory, Algorithms,\nand Systems} [M]. Springer.",
     "\\emph{Scheduling: Theory, Algorithms,\nand Systems} [M]. Springer, pp. 1--897."),
    ("DeepSeek Harness, version 0.2.2-rc.3, CLI coding agent [EB/OL], DeepSeek, 18--22 Nov 2026.",
     "DeepSeek Harness, version 0.2.2-rc.3, CLI coding agent [EB/OL], DeepSeek, 18--22 Nov 2026. \\url{https://www.deepseek.com}, accessed 22 Nov 2026."),
]
for a, b in reps:
    print(s.count(a), a[:40])
    s = s.replace(a, b, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
