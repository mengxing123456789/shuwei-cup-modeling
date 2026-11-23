import io

t = io.open("main.tex", encoding="utf-8").read().splitlines()
for i, l in enumerate(t, 1):
    s = l.strip()
    if (
        s.startswith("\\label{tab:")
        or s.startswith("\\begin{table}")
        or s.startswith("\\end{table}")
        or s.startswith("\\input{tables/tab")
        or s.startswith("\\begin{figure}")
        or s.startswith("\\includegraphics")
        or s.startswith("\\begin{equation}")
    ):
        print(i, s)
