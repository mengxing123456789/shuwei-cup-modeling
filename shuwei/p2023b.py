import zipfile,io,re
from pypdf import PdfReader
zp=r'C:\Users\29900\Downloads\AsterLink\2023第九届数维杯国际赛优秀论文.zip'
z=zipfile.ZipFile(zp)
pick={'A':'A2023101419943.pdf','B':'B2023081819323.pdf','C':'C2023091819503.pdf','D':'D2023091419459.pdf'}
for k,f in pick.items():
    p=[n for n in z.namelist() if n.endswith(f)][0]
    r=PdfReader(io.BytesIO(z.read(p)))
    txt=''.join((r.pages[i].extract_text() or '') for i in range(min(4,len(r.pages))))
    txt=re.sub(r'\s+',' ',txt)
    print('='*20,k,len(r.pages),'pages')
    print(txt[:3000])
    print()
