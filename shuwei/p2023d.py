import zipfile,io,re
from pypdf import PdfReader
zp=r'C:\Users\29900\Downloads\AsterLink\2023第九届数维杯国际赛优秀论文.zip'
z=zipfile.ZipFile(zp)
for k,f in [('C','C2023091819503.pdf'),('D','D2023091419459.pdf')]:
    p=[n for n in z.namelist() if n.endswith(f)][0]
    r=PdfReader(io.BytesIO(z.read(p)))
    print('='*25,k)
    for i in range(2,min(7,len(r.pages))):
        t=re.sub(r'[ \t]+',' ',(r.pages[i].extract_text() or ''))
        if re.search(r'Restatement|Problem|Background|question|Problem Description',t,re.I) and len(t)>200:
            print('--- page',i+1)
            print(t[:2600])
