import pathlib
p = pathlib.Path('main.tex')
s = p.read_text(encoding='utf-8')
old = r"\rhead{\footnotesize Appendix, p.\,\thepage}"
new = r"\rhead{\footnotesize Appendix, p.\,\the\numexpr\thepage-2\relax}"
print('count', s.count(old))
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
