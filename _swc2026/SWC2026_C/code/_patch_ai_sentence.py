import pathlib
p = pathlib.Path('main.tex')
s = p.read_text(encoding='utf-8')
old = "Three statements discharge the notice's substantive requirements."
new = ("Every figure and table in this paper was produced by these scripts, so its caption "
       "is covered by this declaration. Three statements discharge the notice's substantive requirements.")
print('count', s.count(old))
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
