import pathlib, sys
P = pathlib.Path("code/fill_numbers.py"); s = P.read_text(encoding="utf-8")
edits = [
 (r'"FigW":     r"0.50\linewidth"', r'"FigW":     r"0.45\linewidth"'),
 (r'"FigWSmall":     r"0.29\linewidth"', r'"FigWSmall":     r"0.25\linewidth"'),
]
n = 0
for old, new in edits:
    if s.count(old) != 1:
        print("MISS", old, s.count(old)); continue
    s = s.replace(old, new); n += 1
P.write_text(s, encoding="utf-8", newline="\n")
print("fig edits", n)
