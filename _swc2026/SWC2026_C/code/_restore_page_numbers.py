import pathlib
p = pathlib.Path('main.tex')
s = p.read_text(encoding='utf-8')
s = s.replace(r"\newcommand{\bodytotal}{23}", r"\newcommand{\bodytotal}{25}", 1)
s = s.replace(r"\rhead{\small Page \the\numexpr\thepage-2\relax\ of \bodytotal}",
              r"\rhead{\small Page \thepage\ of \bodytotal}")
# appendix header: restore plain thepage
old = r"\rhead{\footnotesize Appendix, p.\,\number\numexpr\csname c@page\endcsname-2\relax}"
new = r"\rhead{\footnotesize Appendix, p.\,\thepage}"
print('appendix count', s.count(old))
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
