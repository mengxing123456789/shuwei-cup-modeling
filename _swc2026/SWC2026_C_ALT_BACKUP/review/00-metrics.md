# 00 口径基线（由 run_review.py metrics 自动生成，不是审读员写的）

生成时刻 2026-11-22 18:48:40　论文目录 `E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP`

## 0. 被测件的身份（先看这一节，再读任何报告）

| 文件 | mtime / 大小 / 摘要 |
|---|---|
| `main.pdf` | 2026-11-22 18:47:23     749460 B  sha256:B393FEAB6468B403EFEBD3C495C123B3 |
| `main.tex` | 2026-11-22 18:47:10      71973 B  sha256:E1CC34C040281A4A475BF5A4FC7E1713 |
| `data/*.json` (13 个) | 最早 15:04:41 → 最新 2026-11-22 18:48:40 |

> **WARNING：数据层比 main.pdf 新 0.02 小时 —— 论文字里的数字可能已被重跑覆盖。**
> 先 `xelatex main.tex` 两次再评，或明确按"落后 N 小时"写进报告（R-V11）。


## 1. 机器判据原始输出

### review_check　exit=0　（python.exe）

```
paper: E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP
pdf: main.pdf   pages: 87
[ OK ] C4    p1 has summary/abstract=True
[ OK ] C4    p2 has contents/directory=False
[ OK ] C5    header lines matched=23
[ OK ] C5    headers leaking identity=0
[ OK ] C7    chinese chars in body=0 (appendix, not judged=0)
[ OK ] C6    total pages=87
[ OK ] C9    appendix=True code=True
[ OK ] C11   placeholder team number hits=0
[ OK ] C11   self-declared invalid identifier in body=0
[ OK ] C11   has References section=True
[ OK ] C8    reference type markers=11

VERDICT: PASS  (fail=0 unknown=0)
```

### gauntlet_check　exit=0　（python.exe）

```
[band] benchmark: E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\refs\official_standard.json  n=48  median sections=8.5
[PASS] paper resolved                      E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP
[PASS] R-V01 body <= 30 pages              body=25 (header numerator of first Appendix A page)
[PASS] R-V02 single denominator            distinct totals=1
[PASS] R-V02 numbers contiguous            header numerators form 1..n with no gaps
[PASS] R-V03 zero CJK in body              body cjk=0 (appendix, not judged=0)
[PASS] R-V04 zero 'university'             hits=0
[PASS] R-V05 team number filled            KNOWN OPEN: \baominghao placeholders must be filled before submission
[PASS] R-W06 no unsupported phrases        no 众所周知/显而易见/obviously,
[PASS] R-W11 front matter order            ['summary', 'contents']
[PASS] R-W04 references have type markers  11 type markers on 13 entries
[PASS] R-W04 >=70% references cited        cite calls=12, [n] uses before bibliography=0, entries=13
[PASS] R-V06 verify_numbers present        claims=284 exit=0
[PASS] R-V09 no stale artefact             KNOWN OPEN (explain each): 9 pair(s): data\alt_p3.json<-code\alt_p3_ccmip.py(25.23h), data\alt_p2_policy.json<-code\alt_p2_data.py(23.96h), data\alt_p2.json<-code\alt_p2_data.py(23.87h) …+6
[PASS] R-V07 band measured on both sides   figures/equations non-zero, so project was read from PDF text
[PASS] R-V07 out-of-band count             ABOVE=['abstract_numbers', 'abstract_density', 'distinct_numbers', 'pct_mentions', 'density_per_100w', 'sections', 'tables', 'references'] BELOW=['abstract_words']
[PASS] R-V14 figure text >= 6 pt           min=4.8 pt median=7.97 pt violations=0 single-char<6pt=6 (measured by python.exe)

16/16 PASS
pdftotext: security risk: running with elevated privileges
```

### figfont　exit=0　（python.exe）

```
pdf: E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.pdf
spans=25389  min=4.8 pt  median=7.97 pt
violations (>= 3 chars and < 6.0 pt): 0
single-character spans below 6.0 pt (not judged): 6
PASS
```

### verify_numbers　exit=0　（python.exe）

```
284 claims, 36 literals, 1 ranges
claims=321 declared=321 checked=321 failures=0 verdict=PASS exit=0
```

### freshness　exit=0　（python.exe）

```
WARN  9 artefact(s) older than a name-matched script:
  data\alt_p3.json                   older than code\alt_p3_ccmip.py         by  25.23 h
  data\alt_p2_policy.json            older than code\alt_p2_data.py          by  23.96 h
  data\alt_p2.json                   older than code\alt_p2_data.py          by  23.87 h
  data\alt_p1.json                   older than code\alt_p1_bocpd.py         by  19.97 h
  data\alt_p2_train.json             older than code\alt_p2_data.py          by  19.09 h
  data\alt_p3.json                   older than code\alt_p3_ab.py            by   5.65 h
  data\alt_p2.json                   older than code\alt_p2_train.py         by   4.71 h
  data\alt_p3.json                   older than code\alt_p3_sweep.py         by   3.53 h
  data\alt_p3.json                   older than code\make_alt_p3_md.py       by   0.03 h
  -> each line needs one sentence: either re-run the script, or say why the artefact is still valid. A green verify_numbers.py does NOT clear this (a stale artefact is exactly what makes it green).
```

## 2. 怎么用这份文件

- 你的结论若与这里的数字不同，并列两个数并写清"我在何时对哪个文件重跑"，不许只写你自己的（R-V11：报告是快照）。
- 这里的 PASS 只覆盖它能自动判的那几条；它**不**等于论文没问题 —— `verify_numbers.py` 绿着也照样可以有数字过期（R-V09）。