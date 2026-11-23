import zipfile,io,sys,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Raw_Data\EgoPro.zip"
zf=zipfile.ZipFile(p)
names=[n for n in zf.namelist() if n.endswith('.csv')]
sess=sorted({n.split('/')[1] for n in names})[0]
print("session",sess)
for n in sorted([x for x in names if x.split('/')[1]==sess]):
    with zf.open(n) as f:
        df=pd.read_csv(f,nrows=2)
    print("--",n.split('/')[-1], "cols",len(df.columns))
    print("   ",list(df.columns)[:14])
