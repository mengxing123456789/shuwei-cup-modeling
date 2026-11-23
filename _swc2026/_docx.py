import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
from docx import Document
p=r"C:\Users\29900\Downloads\AsterLink\2025年第十一届数维杯大学生数学建模挑战赛（秋季赛）承诺书.docx"
d=Document(p)
for i,para in enumerate(d.paragraphs):
    if para.text.strip(): print(i,repr(para.text))
for t in d.tables:
    print("TABLE")
    for row in t.rows:
        print([c.text for c in row.cells])
