import io, sys, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = r'E:\数学建模\_swc2026\46-Modex逆向-技能与质检层.md'
raw = open(p, 'rb').read()
text = raw.decode('utf-8')
lines = text.split('\n')

assert lines[0].startswith('BYTES '), lines[0][:40]
assert lines[-1].strip() == 'VERDICT: PASS' or lines[-2].strip() == 'VERDICT: PASS', repr(lines[-3:])

# fixed-point iteration
guess = 0
for _ in range(40):
    lines[0] = f'BYTES {guess}'
    body = '\n'.join(lines)
    n = len(body.encode('utf-8'))
    if n == guess:
        break
    guess = n

lines[0] = f'BYTES {guess}'
body = '\n'.join(lines)
data = body.encode('utf-8')
with open(p, 'wb') as f:
    f.write(data)

real = os.path.getsize(p)
print('declared', guess, 'real', real, 'match', guess == real)
print('first line:', lines[0])
print('last line:', repr(lines[-1]), repr(lines[-2]))
