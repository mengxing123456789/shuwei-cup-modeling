import zipfile,io,re,sys
from pypdf import PdfReader
sys.stdout.reconfigure(encoding='utf-8',errors='ignore')
zp=r'C:\Users\29900\Downloads\AsterLink\2025年数维杯秋季赛优秀论文.zip'
z=zipfile.ZipFile(zp)
def clean(t):
    t=re.sub(r'[\ud800-\udfff]','',t); return re.sub(r'[ \t]+',' ',t)
jobs=[('B','2025年数维杯秋季赛优秀论文/B题/BSHUWEICUP2549191/BSHUWEICUP2549191.pdf',range(2,6)),
      ('C','2025年数维杯秋季赛优秀论文/C题/CSHUWEICUP2551760/CSHUWEICUP2551760.pdf',range(6,12))]
for k,f,rng in jobs:
    r=PdfReader(io.BytesIO(z.read(f)))
    print('='*25,k)
    for i in rng:
        if i>=len(r.pages): break
        t=clean(r.pages[i].extract_text() or '')
        print(f'--- page {i+1} len={len(t)}')
        print(t[:2300])
