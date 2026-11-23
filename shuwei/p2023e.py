import zipfile,io,re,sys
from pypdf import PdfReader
sys.stdout.reconfigure(encoding='utf-8',errors='ignore')
def clean(t):
    t=re.sub(r'[\ud800-\udfff]','',t)
    return re.sub(r'[ \t]+',' ',t)
zp=r'C:\Users\29900\Downloads\AsterLink\2023第九届数维杯国际赛优秀论文.zip'
z=zipfile.ZipFile(zp)
p=[n for n in z.namelist() if n.endswith('D2023091419459.pdf')][0]
r=PdfReader(io.BytesIO(z.read(p)))
print('='*25,'2023 D')
for i in range(2,min(8,len(r.pages))):
    t=clean(r.pages[i].extract_text() or '')
    if len(t)>300 and re.search(r'question|Problem|Background|laundry|Laundry',t,re.I):
        print('--- page',i+1); print(t[:3200]); break
