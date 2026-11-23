import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

subs = [
    ('$\\hat\\xi_{t+h}$ for\nevery horizon inside the mask from information available at $t$, and compares\nagainst the recorded reference.',
     '$\\hat\\xi_{t+h}$ for\nevery horizon inside the mask from information available at $t$, and compares\nagainst the recorded reference. The removed samples are missing at random with respect\nto the hand trajectory --- the mechanism taxonomy of \\cite{rubin1976} and the estimation\ntreatment of \\cite{little2019} --- which is what makes LOCF and interpolation fair\nreferences rather than straw men.'),
    ('fifteen seeds only, with the official changeover and floor untouched; the rule was then\nfrozen and evaluated on the last fifteen.',
     'fifteen seeds only, with the official changeover and floor untouched; the rule was then\nfrozen and evaluated on the last fifteen --- a rescheduling rule in the sense surveyed by\n\\cite{ouelhadj2009}.'),
    # bibliography: conformal reference and the AI tool entry
    ('\\bibitem{ouelhadj2009}',
     '\\bibitem{vovk2005} Vovk, V., Gammerman, A. and Shafer, G. (2005). \\emph{Algorithmic\nLearning in a Random World}. Springer, New York.\n\\bibitem{deepseek} DeepSeek Harness, command-line coding agent, model routes selected\nduring the window, DeepSeek, used 18--20 November 2026.\n\\bibitem{ouelhadj2009}'),
    # cite the tool inside the AI report
    ('This report follows the organiser\'s notice of November 2026',
     'This report follows the organiser\'s notice of November 2026'),
]

for old, new in subs:
    n = t.count(old)
    print('count=%d anchor=%r' % (n, old[:48]))
    assert n == 1, 'anchor not unique: ' + old[:60]
    t = t.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('written')
print('cites =', t.count('\\cite{'))