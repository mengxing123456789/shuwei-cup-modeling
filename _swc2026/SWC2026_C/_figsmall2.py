import pathlib
P = pathlib.Path("code/fill_numbers.py"); s = P.read_text(encoding="utf-8")
a = '    "FigW": (r"0.50\\linewidth", "layout"),'
b = '    "FigW": (r"0.45\\linewidth", "layout"),'
c = '    "FigWSmall": (r"0.29\\linewidth", "layout"),'
d = '    "FigWSmall": (r"0.25\\linewidth", "layout"),'
assert s.count(a) == 1 and s.count(c) == 1, (s.count(a), s.count(c))
s = s.replace(a, b).replace(c, d)
P.write_text(s, encoding="utf-8", newline="\n")
print("figure widths -> 0.45 / 0.25")
