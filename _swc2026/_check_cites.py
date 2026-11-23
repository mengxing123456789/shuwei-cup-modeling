import io, re

t = io.open(r'E:\数学建模\_swc2026\SWC2026_C\main.tex', encoding='utf-8').read()
cites = re.findall(r'\\cite\{([^}]*)\}', t)
bibs = re.findall(r'\\bibitem\{([^}]*)\}', t)
print('cite count =', len(cites))
print('cited keys =', sorted(set(cites)))
print('bibitem count =', len(bibs))
print('bib keys     =', bibs)
missing = sorted(set(cites) - set(bibs))
print('cited but not in bibliography:', missing if missing else 'none')
unused = sorted(set(bibs) - set(cites))
print('in bibliography but never cited:', unused if unused else 'none')