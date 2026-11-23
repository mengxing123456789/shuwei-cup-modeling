import fitz,sys
d=fitz.open(r'C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\Problem_3_Requirements.pdf')
txt='\n'.join([f'--- PAGE {i+1} ---\n'+pg.get_text() for i,pg in enumerate(d)])
open(r'E:\数学建模\_swc2026\problem_text\C_Problem3_Requirements.txt','w',encoding='utf-8').write(txt)
print('C_Problem3_Requirements.txt', d.page_count, len(txt))
