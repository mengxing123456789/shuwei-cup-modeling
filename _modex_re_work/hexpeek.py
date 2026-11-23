import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_modex_re_work\zlib3\writing_guide_25770.txt'
raw = open(p, 'rb').read()
i = raw.find('论证主线'.encode('utf-8'))
print('idx', i)
print(raw[max(0,i-200):i+200])
print()
print(repr(raw[max(0,i-120):i+120]))
