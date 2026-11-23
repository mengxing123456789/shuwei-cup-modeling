# -*- coding: utf-8 -*-
"""Strip LaTeX to plain prose for AI-tone detection."""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

src = io.open(os.path.join(PROJ, "main.tex"), encoding="utf-8").read()
i = src.find(r"\begin{document}")
body = src[i:]

ENVS = ["table", "longtable", "tabular", "figure", "equation", "align",
        "align*", "lstlisting", "thebibliography", "algorithm", "algorithmic"]
for env in ENVS:
    body = re.sub(r"\\begin\{%s\}.*?\\end\{%s\}" % (re.escape(env), re.escape(env)),
                  " ", body, flags=re.S)

body = re.sub(r"\$[^$]*\$", " X ", body)          # inline math
body = re.sub(r"\\\[.*?\\\]", " X ", body, flags=re.S)
body = re.sub(r"\\[a-zA-Z]+\*?", " ", body)        # commands
body = re.sub(r"[{}]", " ", body)
body = re.sub(r"%.*", " ", body)
body = re.sub(r"[ \t]+", " ", body)
body = re.sub(r"\n\s*\n+", "\n\n", body)
body = body.strip()

out = os.path.join(os.path.dirname(PROJ), "_paper_plain.txt")
io.open(out, "w", encoding="utf-8").write(body)
print("chars", len(body), "words", len(body.split()))
print("written", out)
