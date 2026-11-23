# -*- coding: utf-8 -*-
"""Fix the doubled period after section numbers in the contents (the class
already prints the number's own period) and give the page a little more air."""
import io

P = r"main.tex"
s = io.open(P, encoding="utf-8").read()

old = "\\titlecontents{section}[0pt]{\\bfseries\\addvspace{3pt}}%\n  {{\\thecontentslabel}.\\enspace}{}%"
new = "\\titlecontents{section}[0pt]{\\bfseries\\addvspace{4pt}}%\n  {{\\thecontentslabel}\\enspace}{}%"
assert old in s
s = s.replace(old, new, 1)

s = s.replace("{\\linespread{1.0}\\selectfont", "{\\linespread{1.05}\\selectfont", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("section labels de-doubled; contents leading 1.05")
