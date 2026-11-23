import fitz, os, json, glob
base=r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题'
out=r'E:\数学建模\_sw2026\rawtext'
files=[]
for p in glob.glob(os.path.join(base,'*题','*.pdf'))+glob.glob(os.path.join(base,'*.pdf')):
    files.append(p)
for p in sorted(files):
    try:
        d=fitz.open(p)
        txt='\n'.join(page.get_text() for page in d)
        name=os.path.splitext(os.path.basename(p))[0]
        safe=''.join(c if c.isalnum() or c in '_-' else '_' for c in name)[:80]
        fp=os.path.join(out,safe+'.txt')
        open(fp,'w',encoding='utf-8').write(txt)
        print(f'{len(d)}p {len(txt)}chars -> {fp}')
    except Exception as e:
        print('ERR',p,e)