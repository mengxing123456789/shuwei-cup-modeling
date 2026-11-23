# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(__file__).resolve().parent.parent / "main.tex"
s = p.read_text(encoding="utf-8")
a = """Two layers carry the decision: the predictor that turns a prefix into a completion
time, and the rule that turns a completion time into a start time. We perturb each
layer separately and report what moves.

The predictor layer is tested by refitting the ridge model under four feature subsets
and four context lengths, holding the mask and the split fixed."""
b = """The predictor layer is refitted under four feature subsets and four context
lengths, holding the mask and the split fixed."""
assert a in s
s = s.replace(a, b)
a2 = """The model rests on eight assumptions. Each is stated where it is first used, and
Appendix~\\ref{app:assumptions} registers it against the evidence that supports it."""
b2 = """Eight assumptions carry the model; Appendix~\\ref{app:assumptions} registers each
against the evidence that supports it."""
assert a2 in s
s = s.replace(a2, b2)
p.write_text(s, encoding="utf-8")
print("ok", len(s.encode("utf-8")))
