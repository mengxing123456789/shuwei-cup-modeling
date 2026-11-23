import pathlib
root = pathlib.Path(r'.\_swc2026')
for name in ['43-官方格式核对与图表重做.md','45-逐问复查与参数核对.md','47-备用稿与获奖论文对比评估.md']:
    p = root/name
    s = p.read_text(encoding='utf-8')
    s = s.replace('2,475,490', '2,475,359').replace('12,695,665', '12,700,761').replace('12,695,692','12,700,761')
    s = s.replace('1,996,415', '2,475,359')
    p.write_text(s, encoding='utf-8', newline='\n')
print('done')
