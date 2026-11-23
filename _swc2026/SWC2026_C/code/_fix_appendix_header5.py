import pathlib
p = pathlib.Path('main.tex')
s = p.read_text(encoding='utf-8')
old = r"\rhead{\footnotesize Appendix, p.\,\number\numexpr\csname c@page\endcsname-2\relax}"
new = "% numerals-ok: begin\n" + old + "\n% numerals-ok: end"
print('count', s.count(old))
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
