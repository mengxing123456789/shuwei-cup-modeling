import fitz,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\Problem_3_Requirements.pdf"
d=fitz.open(p); print("pages",len(d))
t="".join(x.get_text() for x in d)
print("chars",len(t)); print(t[:5000])
