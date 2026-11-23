import io, re

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

# Move the 11-metric scorecard table out of the body into Appendix N.
start = t.find(r"\input{tables/tab_p3_scorecard.tex}")
if start < 0:
    raise SystemExit("scorecard input not found")

# replace the include with a pointer sentence
t = t.replace(r"\input{tables/tab_p3_scorecard.tex}",
              r"The full table, one row per policy and one column per measure, is "
              r"Table~\ref{tab:p3score} in Appendix~\ref{app:ablation}.")

# and make the lead-in reference the appendix table
t = t.replace(
 r"""The statement asks for eleven measures for every method, not only the rate, so
Table~\ref{tab:p3score} reports all of them on the same seeds and the same sampler.""",
 r"""The statement asks for eleven measures for every method, not only the rate, so
Table~\ref{tab:p3score} in Appendix~\ref{app:ablation} reports all of them on the same seeds
and the same sampler.""")

io.open(P, "w", encoding="utf-8", newline="").write(t)

# append the table to app_n
A = "tables/app_n.tex"
a = io.open(A, encoding="utf-8").read()
tab = io.open("tables/tab_p3_scorecard.tex", encoding="utf-8").read()
if r"\label{tab:p3score}" not in a:
    if r"\subsection{Tables moved out of the body}" in a:
        a = a.replace(r"\subsection{Tables moved out of the body}",
                      r"\subsection{Tables moved out of the body}" + "\n\n" + tab, 1)
    else:
        a = a.rstrip() + "\n\n" + tab
    io.open(A, "w", encoding="utf-8", newline="").write(a)
    print("appended scorecard to app_n")
else:
    print("scorecard already in app_n")
print("main.tex rewritten")
