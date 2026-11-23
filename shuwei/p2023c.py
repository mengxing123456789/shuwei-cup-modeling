import zipfile,io,re
from pypdf import PdfReader
zp=r'C:\Users\29900\Downloads\AsterLink\2023第九届数维杯国际赛优秀论文.zip'
z=zipfile.ZipFile(zp)
pick={'C':'C2023091819503.pdf','D':'D2023091419459.pdf'}
for k,f in pick.items():
    p=[n for n in z.namelist() if n.endswith(f)][0]
    r=PdfReader(io.BytesIO(z.read(p)))
    txt=''.join((r.pages[i].extract_text() or '') for i in range(1,min(6,len(r.pages))))
    txt=re.sub(r'[ \t]+',' ',txt)
    print('='*25,k)
    # find restatement part
    print(txt[:4200])
    print()
