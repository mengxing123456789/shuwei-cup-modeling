# -*- coding: utf-8 -*-
"""Count in-text figure references / figure captions in the 22 award papers.
Purpose: give the 07-figures.md review a citable base rate instead of impression."""
import pathlib, re, sys, json

sys.stdout.reconfigure(encoding='utf-8')
base = pathlib.Path(r'E:\数学建模\APMCM-PROBLEMS\_award_text')
rows = []
for p in sorted(base.glob('*.txt')):
    t = p.read_text(encoding='utf-8', errors='replace')
    # in-text pointer: "shown in Figure 3", "as Fig. 2", "see Figure 5", "如图3"
    intext = re.findall(r'(?i)(?:shown\s+in|as\s+shown\s+in|see|in|from)\s+(?:Figure|Fig\.?)\s*\d+', t)
    intext_cn = re.findall(r'(?:如|见|由|从)\s*图\s*\d+', t)
    figword = re.findall(r'(?i)\bFigure\s*\d+', t)
    figcn = re.findall(r'图\s*\d+', t)
    tabword = re.findall(r'(?i)\bTable\s*\d+', t)
    tabcn = re.findall(r'表\s*\d+', t)
    # caption-ish: "Figure 3:" or "图3 " followed by a title
    cap = re.findall(r'(?i)\b(?:Figure|Fig\.?)\s*\d+\s*[:.\u3001]', t)
    rows.append(dict(file=p.name, intext=len(intext) + len(intext_cn),
                     figword=len(figword), figcn=len(figcn),
                     tab=len(tabword) + len(tabcn), cap=len(cap)))

hdr = '%-44s %7s %8s %7s %6s %6s' % ('file', 'intext', 'FigN', 'FigCN', 'Tab', 'capish')
print(hdr)
print('-' * len(hdr))
for r in rows:
    print('%-44s %7d %8d %7d %6d %6d' % (r['file'], r['intext'], r['figword'], r['figcn'], r['tab'], r['cap']))

n = len(rows)
print()
print('papers total                              : %d' % n)
print('papers with >=1 in-text figure pointer     : %d/%d' % (sum(1 for r in rows if r['intext'] > 0), n))
print('papers with >=1 "Figure N"/"图N" token      : %d/%d' % (sum(1 for r in rows if r['figword'] + r['figcn'] > 0), n))
print('papers with >=1 "Table N"/"表N" token       : %d/%d' % (sum(1 for r in rows if r['tab'] > 0), n))
print('total in-text figure pointers             : %d' % sum(r['intext'] for r in rows))
print('total figure tokens                       : %d' % sum(r['figword'] + r['figcn'] for r in rows))
print('total table tokens                        : %d' % sum(r['tab'] for r in rows))
print('papers whose in-text pointers == 0         : %s' %
      ', '.join(r['file'] for r in rows if r['intext'] == 0))
json.dump(rows, open(base.parent / '_award_figref.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
