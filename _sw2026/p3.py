import pymupdf
p=r'C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\Problem_3_Requirements.pdf'
d=pymupdf.open(p)
print('\n'.join(page.get_text() for page in d))