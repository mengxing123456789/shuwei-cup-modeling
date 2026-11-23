import zipfile,io,re,glob,os
from pypdf import PdfReader
zp=r'C:\Users\29900\Downloads\AsterLink\2023年数维杯国际赛优秀论文.zip'
if not os.path.exists(zp):
    cands=[f for f in glob.glob(r'C:\Users\29900\Downloads\AsterLink\*2023*')]
    print('CAND',cands); zp=cands[0] if cands else None
z=zipfile.ZipFile(zp)
names=[n for n in z.namelist() if n.lower().endswith('.pdf')]
print('pdf count',len(names))
# group by problem letter from path
groups={}
for n in names:
    m=re.search(r'([ABCD])[^/\\]*$',n) or re.search(r'([ABCD])',n.split('/')[1] if len(n.split('/'))>1 else n)
    if m: groups.setdefault(m.group(1),[]).append(n)
for k in sorted(groups):
    print(k,len(groups[k]))
    print('   ',groups[k][0])
