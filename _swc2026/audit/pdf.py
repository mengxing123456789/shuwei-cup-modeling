# -*- coding: utf-8 -*-
import fitz, os
p = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\Problem_3_Requirements.pdf'
OUT = r'E:\数学建模\_swc2026\audit'
doc = fitz.open(p)
L = ['pages=%d  metadata=%s' % (doc.page_count, doc.metadata)]
for i, page in enumerate(doc):
    t = page.get_text('text')
    L.append('\n========== PAGE %d (%d chars) ==========' % (i + 1, len(t)))
    L.append(t)
open(os.path.join(OUT, 'p3_pdf.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('pages', doc.page_count, 'total chars', sum(len(pg.get_text()) for pg in doc))