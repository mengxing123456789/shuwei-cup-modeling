# 00 口径基线（由 run_review.py metrics 自动生成，不是审读员写的）

生成时刻 2026-11-20 11:12:23　论文目录 `E:\数学建模\_swc2026\SWC2026_A`

## 0. 被测件的身份（先看这一节，再读任何报告）

| 文件 | mtime / 大小 / 摘要 |
|---|---|
| `main.pdf` | 2026-11-20 11:10:01     451432 B  sha256:A07B0CBEFCD1897F6F03CC21E9649E0D |
| `main.tex` | 2026-11-20 11:09:33      48630 B  sha256:78ED6F265289B0F2159005FD0FDBCC7A |
| `data/*.json` (8 个) | 最早 10:42:17 → 最新 2026-11-20 10:53:32 |

## 1. 机器判据原始输出

### review_check　exit=0　（python.exe）

```
paper: E:\数学建模\_swc2026\SWC2026_A
pdf: main.pdf   pages: 24
[ OK ] C4    p1 has summary/abstract=True
[ OK ] C4    p2 has contents/directory=False
[ OK ] C5    header lines matched=23
[ OK ] C5    headers leaking identity=0
[ OK ] C7    chinese chars in body=0 (appendix, not judged=0)
[ OK ] C6    total pages=24
[ OK ] C9    appendix=True code=True
[ OK ] C11   placeholder team number hits=0
[ OK ] C11   self-declared invalid identifier in body=0
[ OK ] C11   has References section=True
[ OK ] C8    reference type markers=12

VERDICT: PASS  (fail=0 unknown=0)
```

### gauntlet_check　exit=0　（python.exe）

```
[band] benchmark: E:\数学建模\_swc2026\SWC2026_A\refs\official_standard.json  n=16  median sections=13.5
[PASS] paper resolved                      E:\数学建模\_swc2026\SWC2026_A
[PASS] R-V01 body <= 30 pages              body=23 (header numerator of first Appendix A page)
[PASS] R-V02 single denominator            distinct totals=1
[PASS] R-V02 numbers contiguous            header numerators form 1..n with no gaps
[PASS] R-V03 zero CJK in body              body cjk=0 (appendix, not judged=0)
[PASS] R-V04 zero 'university'             hits=0
[PASS] R-V05 team number filled            KNOWN OPEN: \baominghao placeholders must be filled before submission
[PASS] R-W06 no unsupported phrases        no 众所周知/显而易见/obviously,
[PASS] R-W11 front matter order            ['summary', 'contents']
[PASS] R-W04 references have type markers  12 type markers on 12 entries
[PASS] R-W04 >=70% references cited        cite calls=25, [n] uses before bibliography=0, entries=12
[PASS] R-V06 verify_numbers present        claims=116 exit=0
[PASS] R-V09 no stale artefact             KNOWN OPEN (explain each): none
[PASS] R-V07 band measured on both sides   figures/equations non-zero, so project was read from PDF text
[PASS] R-V07 out-of-band count             ABOVE=['abstract_numbers', 'abstract_density', 'distinct_numbers', 'pct_mentions', 'density_per_100w', 'tables', 'references'] BELOW=['figures']
[PASS] R-V14 figure text >= 6 pt           min=5.98 pt median=11.96 pt violations=0 single-char<6pt=53 (measured by python.exe)

16/16 PASS
pdftotext: security risk: running with elevated privileges
```

### figfont　exit=0　（python.exe）

```
pdf: E:\数学建模\_swc2026\SWC2026_A\main.pdf
spans=5333  min=5.98 pt  median=11.96 pt
violations (>= 3 chars and < 6.0 pt): 0
single-character spans below 6.0 pt (not judged): 53
PASS
```

### verify_numbers　exit=0　（python.exe）

```
116 claims passed, 0 failed
failures=0
```

### freshness　exit=0　（python.exe）

```
PASS  no script is newer than a name-matched artefact
```

## 2. 怎么用这份文件

- 你的结论若与这里的数字不同，并列两个数并写清"我在何时对哪个文件重跑"，不许只写你自己的（R-V11：报告是快照）。
- 这里的 PASS 只覆盖它能自动判的那几条；它**不**等于论文没问题 —— `verify_numbers.py` 绿着也照样可以有数字过期（R-V09）。