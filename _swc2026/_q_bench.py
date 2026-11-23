import glob, fitz, re
root = r'C:\Users\29900\Downloads\AsterLink'
hits = glob.glob(root + r'\**\*B2024093029335*', recursive=True)
print('files', hits[:5])
for h in hits[:2]:
    if h.lower().endswith('.pdf'):
        doc = fitz.open(h)
        txt = ''.join(p.get_text() for p in doc)
        print(h.split('\\')[-1], 'pages', doc.page_count, 'chars', len(txt))
        print('  RMSE count', len(re.findall(r'RMSE', txt)))
        print('  train/test count', len(re.findall(r'train|test|训练|测试', txt, re.I)))
        print('  R2 count', len(re.findall(r'R2|R\^2|R²', txt)))
