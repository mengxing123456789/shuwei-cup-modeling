import io

fp = r'E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py'
s = io.open(fp, encoding='utf-8').read()
s = s.replace('"FigW": (r"0.68\\linewidth", "layout")', '"FigW": (r"0.60\\linewidth", "layout")')
s = s.replace('"FigWSmall": (r"0.46\\linewidth", "layout")', '"FigWSmall": (r"0.40\\linewidth", "layout")')
io.open(fp, 'w', encoding='utf-8', newline='\n').write(s)

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

old = ('The duration side points the same way. The selected prefix regression has test MAE\n'
       '\\slotPDurSelTestMAE{} s against \\slotPDurFreeBaseMAE{} s for the family-median constant\n'
       'on the same split, so the scheduling gain comes from the policy and its online map\n'
       'estimate, not from a superior duration model; the removable part of the error is bounded,\n'
       'so only a different observation regime could move it, which Part II prices and answers\n'
       'negatively at the current prefix quality.')
new = ('The duration side points the same way: the prefix regression reaches test MAE\n'
       '\\slotPDurSelTestMAE{} s against \\slotPDurFreeBaseMAE{} s for the family median, so the\n'
       'scheduling gain comes from the policy, not from a superior duration model, and only a\ndifferent observation regime could move the residual.')
print('para count =', t.count(old))
assert t.count(old) == 1
t = t.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('written')