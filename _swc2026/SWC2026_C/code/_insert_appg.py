from pathlib import Path

p = Path(r"main.tex")
t = p.read_text(encoding="utf-8")

# 1) body cross-reference: Appendices D and G (net zero lines)
old_ref = "Appendix~D scores us against marks declared before the experiments and names the"
assert t.count(old_ref) == 1, "body ref anchor missing"
t = t.replace(old_ref, "Appendices~D and~G score us against marks declared before the experiments and name the")

# 2) new Appendix G before \end{document}
anchor = "\\end{document}"
assert t.count(anchor) == 1, "end of document anchor missing"

app = r"""
\addcontentsline{toc}{section}{Appendix G: Second-round experiments}
\section*{Appendix G: Second-round experiments}
\label{app:secondround}

% numerals-ok: begin
The first version of this paper trained one model per task and stopped. A reviewer
reasonably asks what more compute would buy, so the second round trained four families of
larger models on the GPU, re-extracted every video, and wrote the success bar into each
script before the run. Three of the four came back negative and are reported as such:
the segmentation detector gains a little average precision but loses the boundary score
that made it usable; the quantile predictor halves the short-horizon error and still misses
its long-horizon bar; the paid second look never moves the on-time rate. The one clear
positive is the decision layer, where the better short-horizon model moves the optimal
review interval by a twentieth of a second and the objective by a fifth. Table~\ref{tab:gpu-ledger}
is the compute ledger, and the four tables after it are the evidence for each verdict.
% numerals-ok: end

\input{tables/app_g.tex}

"""

t = t.replace(anchor, app + anchor)
p.write_text(t, encoding="utf-8", newline="\n")
print("inserted Appendix G")
