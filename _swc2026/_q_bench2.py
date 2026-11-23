import pymupdf, re
h = r'C:\Users\29900\Downloads\AsterLink\B2024093029335.pdf'
doc = pymupdf.open(h)
txt = ''.join(p.get_text() for p in doc)
pats = {
 'RMSE(exact)': r'RMSE',
 'RMSE(带数值=)': r'RMSE\s*[=:：]',
 'rmse(不分大小写)': r'(?i)rmse',
 'train(整词)': r'\btrain\b',
 'test(整词)': r'\btest\b',
 'train/test 组合': r'\btrain\s*/\s*test\b',
 '训练': r'训练',
 '测试': r'测试',
 '验证': r'验证',
 'R2/R^2/R²': r'R2|R\^2|R²',
}
for k, p in pats.items():
    print(f'{k:18s}', len(re.findall(p, txt)))
print('pages', doc.page_count, 'chars', len(txt))
print('\n--- 含 train 的上下文样本 ---')
for m in list(re.finditer(r'\btrain\b', txt))[:5]:
    print(repr(txt[max(0,m.start()-60):m.start()+60]))
