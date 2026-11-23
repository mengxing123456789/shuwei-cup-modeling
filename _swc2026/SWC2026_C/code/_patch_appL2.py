import pathlib
p = pathlib.Path(r"code\make_appendix_l.py")
t = p.read_text(encoding="utf-8")
t = t.replace(r'Separator~\ref{sec:p3sched}', r'Separator~\ref{sec:p3model}')
t = t.replace('Section~\\ref{sec:p3sched} reports a different pair', 'Section~\\ref{sec:p3model} reports a different pair')
t = t.replace(r'rows.append(r"\begin{table}[H]\centering\small")' + '\n' + 'rows.append(r"\\caption{P1-a model ladder.', r'rows.append(r"\begin{table}[H]\centering\scriptsize")' + '\n' + 'rows.append(r"\\caption{P1-a model ladder.')
old = 'rows.append(rf"\\noindent\\footnotesize Sources: \\texttt{{up2\\_benchmark.json}} ({sha(D/\'up2_benchmark.json\')[:16]}\\ldots), \\texttt{{p2\\_official\\_distance.json}} ({sha(D/\'p2_official_distance.json\')[:16]}\\ldots), \\texttt{{p3\\_official\\_audit.json}} ({sha(D/\'p3_official_audit.json\')[:16]}\\ldots), \\texttt{{p1a\\_zero\\_param.json}} ({sha(D/\'p1a_zero_param.json\')[:16]}\\ldots).")'
new = 'rows.append(rf"\\noindent\\footnotesize Sources: \\texttt{{up2\\_benchmark.json}} ({sha(D/\'up2_benchmark.json\')[:16]}\\ldots), \\texttt{{p2\\_official\\_distance.json}} ({sha(D/\'p2_official_distance.json\')[:16]}\\ldots),")' + '\n' + 'rows.append(rf"\\texttt{{p3\\_official\\_audit.json}} ({sha(D/\'p3_official_audit.json\')[:16]}\\ldots), \\texttt{{p1a\\_zero\\_param.json}} ({sha(D/\'p1a_zero_param.json\')[:16]}\\ldots), \\texttt{{up2\\_p1b.json}} ({sha(D/\'up2_p1b.json\')[:16]}\\ldots).")'
if old not in t:
    raise SystemExit("source line MISS")
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("patched")
