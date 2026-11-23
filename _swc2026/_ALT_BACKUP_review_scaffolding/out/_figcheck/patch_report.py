# -*- coding: utf-8 -*-
"""Patch review/07-figures.md in place by line range, then fix BYTES.

Line numbers refer to the 381-line version read at 18:04.
Replacements are applied bottom-up so earlier indices stay valid.
"""
import sys, io, pathlib

sys.stdout.reconfigure(encoding='utf-8')
P = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\review\07-figures.md')
raw = P.read_bytes()
assert not raw.startswith(b'\xef\xbb\xbf'), 'file has BOM'
text = raw.decode('utf-8')
lines = text.split('\n')
print('lines before:', len(lines))
print('L1:', repr(lines[0]))
print('last:', repr(lines[-1]))


def put(start, end, new):
    """Replace 1-based inclusive range [start, end] with the list new."""
    lines[start - 1:end] = new


# ---------------------------------------------------------------- §6 结论
put(368, 381, """## 6. 结论

**判 FAIL。** 三条机器口径全过（review_check PASS、gauntlet 16/16、figfont PASS），所以剩下的是**必须读出来的问题**，共 8 类：

1. **图3 只画有利的一半** —— 正文 main.tex:150 自陈段级组内 LOO AUC = **0.076**（低于随机、方向相反），图里 0.914/0.915 两根在、它不在。另：main.tex:150 说"record-level scores have a within-record AUC of exactly 0.500 by construction"，实测 `downstream_auc.within_record.mean_auc` = {hierarchical_looo 0.0759, record_posterior_bound **0.5648**, raw_record_bad_rate 0.5000, official_eligible_flag 0.5000, oracle 1.0000} —— **只有两个恰好 0.500，posterior bound 是 0.565**，正文的"by construction"对它不成立。这是本报告最重的一条。
2. **敏感性只画有利的一半，且正文的 0.046 属于另一个参数** —— tab:p1sens 的 8 行其实只有 **7 个不同配置**（hazard=4 与 sigma=0.4 是同一格），正文 main.tex:173 却说 "Eight configurations"；表只印 Count MAE / F1@0.5s / F1@2s，**不印 F1@5s**（`micro_f1_5`），而选中的格在 F1@0.5s 与 F1@2s 上都是 7 格中的**第 1**、在 F1@5s 上是**第 2**、在 Count MAE 上是第 2。更硬的是 main.tex:365 "moving it [hazard] by a factor of two changes F1 by 0.046"：hazard 的 F1@0.5s 全距只有 **0.03912**（2→4 得 +0.03522、4→8 得 −0.03912），而 **0.04612 正是 sigma 的全距** —— 正文把 sigma 的摆幅记在了 hazard 名下，并据此说"hazard 是唯一要紧的参数"，与表相反。
3. **图2(b) 基线三元组硬编码**（`alt_figures.py:171`），有产物键却没读；图1 的 69/66,070/349 同病。任务契约"印出来的数必须能被别人复算"在此断裂。
4. **图5 与 caption 互相否认** —— 虚线连 A→C 画成平滑斜坡，caption 说 "step function: buy none or buy both"；caption 又称 A/C 为 "interior points"，而它们是端点。
5. **图5 三选项 n 不等（A 221 / B·C 300）却被 caption 说成 "same windows"** —— 可复算的样本量矛盾。
6. **零误差带**（实测 0 条 whisker，五张图）；图4 的 "never worse than holding" 在 L=1.0 处只有 0.37 pt，小于线宽；而 `rmse_cm` / `p90_cm` 就在同一行 JSON 里，画带零成本。
7. **图2(a) 把有序数值摊成等距类别轴**（页间距极差 0.000 pt vs 数值间距 10.0×），**图3 x 轴跑到 1.300**（超度量上界 30 %），**图5 y 轴截断到数据范围的 59 %**（零点在可见底边下 1.8 个轴高）—— 三种刻度误用各一处，全部无断轴符号。
8. **六范式缺 4 个**：热力图（6/22 一等奖用过，Q3 的 3×5×4 网格正是标准形态）、Pareto 拐点（5/22 用过，图5 有前沿实质却不标拐点）、雷达（1/22，建议项）、龙卷风/秩漂移（0/22，但敏感性表只扫 2 参数、merge threshold 与 drop fraction **根本没扫** —— `min_seg_s` 与 `map_drop` 在全部 8 个 JSON 里各只出现 1 次，就是 config 里的选定值，所以 main.tex:365 "the merge threshold and the drop fraction move it by less than 0.01" **没有产物键**）。

**改法优先级**：图3 重画（补 0.076 与 0.500/0.565 参照柱 + CI）> 敏感性补龙卷风图并补印 F1@5s、改正 0.046 的归属 > 图5 重画（阶梯线 + 从 0 起 + break-even 竖线）+ 改 caption（n 不等）> 图2 重画（数值轴 + 读 JSON）> 图4 重画（加 rmse/p90 带 + 内嵌放大）> 图1 重画（补两条箭头 + 图例）> 正文补 5 处 `\\ref{fig:}` > 补 Q3 热力图与雷达。

VERDICT: FAIL""")

# ---------------------------------------------------------------- §5 复算命令
put(362, 364, """# 8) 22 篇一等奖的图引用与范式基线（§1.1）
cd $R; & $PY out\\_figcheck\\award_figref.py

# 9) 图3/图4 图内每一个字的字号与坐标（§3.5、§3.6）
cd $R; & $PY out\\_figcheck\\fig_text.py

# 10) 图2(a) 的 F1 拆成 precision/recall（§3.2）
cd $R; & $PY out\\_figcheck\\fig1_pr.py

# 11) 敏感性：8 行几个不同配置、选中格在四个指标上的名次（§3.7）
cd $R; & $PY out\\_figcheck\\sens_rank.py

# 12) 0.046 属于哪个参数、merge/drop 有无扫描、组内 AUC 是否恰好 0.500（§3.7、§3.4）
cd $R; & $PY out\\_figcheck\\sens_claims.py
```""")

# ---------------------------------------------------------------- §4.4
put(323, 325, """### 4.4 多重比较

图3 一张图 4 个 AUC 的比较、图2(a) 一张图 8 根柱的比较、图4 一张图 12 个点的比较，**全部无任何校正**（无 BH/Bonferroni 后的 q，无 family-wise 说明）。最尖锐的是图3：4 个 AUC 两两比 = 6 对，其中 0.914/0.915 这一对差 1.0 % 个 CI 宽被当结果。按任务契约"同一张表 k 个检验，必须给 BH/Bonferroni 后的 q"，此处 **k=6 而 q 一个都没有**。

敏感性侧同一个病、另一种形态（§3.7）：8 行里选中的格在三个已印指标上是第 1/1/2 名，**没印的 F1@5s 上它是第 2 名（最好的是 hazard=2 的 0.65896）**。多指标择优不校正、且择优用的指标恰好是已印的三个，这是"用同一份数据既选参数又报性能"的选择性偏倚，比缺 q 值更实。""")

# ---------------------------------------------------------------- §3.7 新增
put(296, 296, """### 3.7 敏感性：表格形态下的"只画有利的一半"

论文没有敏感性图（P2 缺失），敏感性全部落在 `tab:p1sens`（main.tex:175-191）。表格同样能犯"只画有利的一半"，而且这里犯了三重（`out\\_figcheck\\sens_rank.py`、`sens_claims.py`）：

**一、8 行不是 8 个配置。** 按四个指标的完整元组去重，8 行只有 **7 个不同配置** —— `hazard_lambda_s=4` 与 `sigma_s=0.4` 是同一格（两行数值逐位相同：mae 2.94203、f1@.5 0.18262、f1@2 0.58027、f1@5 0.65390）。正文 main.tex:173 写 "Eight configurations were re-run"，实际是 7 个配置 + 1 个重复的基准行。这不算造假（重复印基准行是常规做法），但"8 个配置"这句话是错的，且它让"扫了 8 次"的印象强于事实。

**二、选中的格在未印的那一列上不是最好。**

| 指标 | 选中格 | 名次（7 格） | 最好 | 最差 | 表里印了吗 |
|---|---|---|---|---|---|
| Count MAE | 2.94203 | **2/7** | 2.88406（sigma=0.6） | 3.13043 | 印了 |
| F1@0.5s | 0.18262 | **1/7** | 0.18262 | 0.13650 | 印了 |
| F1@2s | 0.58027 | **1/7** | 0.58027 | 0.52915 | 印了 |
| F1@5s | 0.65390 | **2/7** | 0.65896（hazard=2） | 0.63677 | **没印** |

表印的三列里，选中格有两列是第 1；唯一不是第 1 的那一列（Count MAE，第 2）还在表里，而**它也不是第 1 的那一列（F1@5s）被整列省掉了**。JSON 里 `micro_f1_5` 是逐行都有的字段，省掉它是选择而非数据限制。这不是"图只画有利的一半"，是"表只印有利的三列"，同一个病。

**三、正文把 sigma 的摆幅记在 hazard 名下。** main.tex:365 写 "The hazard rate is the only parameter that matters: moving it by a factor of two changes $F_1$ by 0.046"：

| 参数 | F1@0.5s 全距 | 扫描跨度 | 表里相邻 2× 步长的实际变化 |
|---|---|---|---|
| hazard_lambda_s | **0.03912** | 2→8（4.00×） | 2→4: **+0.03522**；4→8: **−0.03912** |
| sigma_s | **0.04612** | 0.25→0.6（2.40×） | 无 2× 步长（0.25→0.4 是 1.6×） |

**0.046 精确对上 sigma 的全距 0.04612，对不上 hazard 的 0.03912**；而且 sigma 的摆幅（0.04612）比 hazard 的（0.03912）**大 18 %**，所以"hazard 是唯一要紧的参数"被这张表本身否证。另外"factor of two"在表里没有对应的相邻行：hazard 的 2× 邻居是 2→4 与 4→8（跨行），两者给出 +0.035 与 −0.039，都不是 0.046。这条是**可复算的正文与产物冲突**，比缺图严重。

**四、两个参数根本没扫。** `min_seg_s=3.0` 与 `map_drop=0.3` 在 `data/*.json` 全部 8 个文件里**各只出现 1 次**（就是 `config` 里的选定值），没有任何 sweep 记录。所以 main.tex:365 "the merge threshold and the drop fraction move it by less than 0.01" 这句话**在产物里找不到任何依据** —— 按任务契约"找不到产物键的数字是缺陷本身"，这不是"需要更精确"，是**没有测过**。

**范式判读**：敏感性在六范式里应做成龙卷风（每参数 ±1 档对三指标的摆幅，一眼看出 sigma 的条形比 hazard 长）或秩漂移（7 个配置在三个指标下的排序是否翻转 —— 本例中 Count MAE 的第 1 是 sigma=0.6，F1@0.5s 的第 1 是 hazard=4，**排序确实翻转**，正是秩漂移图要展示的现象）。目前是一张 5 列 8 行的表，读者要自己算全距才能发现正文说反了。""")

# ---------------------------------------------------------------- §3.4 补 0.5648
put(263, 263, """**只画有利的一半**（最重的一条）：正文 main.tex:150 明写段级组内 LOO AUC = **0.076**（低于随机、方向相反）。图3 画了 0.914 与 0.915 两根，**0.076 一根都没有**。也就是说：正文用一整句自我否认的数，图把它当成主结果展示。这正对应任务里"敏感性是否只画了有利的一半"这一判据 —— 此处不是敏感性图，但**同一个病**：选择性展示。

同一句还有一个可复算的偏差。main.tex:150 说 "the record-level scores have a within-record AUC of exactly 0.500 by construction"，而 `downstream_auc.within_record.mean_auc`（n_records=21, n_segments=162）实测是：

| 方法 | 组内 mean AUC | 是否"恰好 0.500" |
|---|---|---|
| record_posterior_bound | **0.5647683** | 否 |
| raw_record_bad_rate | 0.5000000 | 是 |
| official_eligible_flag | 0.5000000 | 是 |
| hierarchical_looo | 0.0759127 | 否（正文引用的就是这个 0.076） |
| oracle_segment_bad_rate | 1.0000000 | 否（上界参照） |

"exactly 0.500 by construction" 只对 `raw_record_bad_rate` 与 `official_eligible_flag` 成立；**`record_posterior_bound` 在组内其实是 0.565，高于随机 0.065**。所以正文那句话把三个方法一起按"0.500"处理，而图3 缺的那根参照柱应该是 0.565 而不是 0.500 —— 若照 0.500 补柱，会把 posterior bound 的真实组内表现**再压低 6.5 个点**，是补图时必须用对的那个数。""")

# ---------------------------------------------------------------- §0.5 同代核对
put(87, 102, """### 0.5 被测件与数据层同代核对（R-V11：报告是快照）

`00-metrics.md` 记录的被测件是 **17:40:29 / sha256 378EED5F** 的 main.pdf；我在 18:03 复核时磁盘上的 main.pdf 已经是 **17:53:40 / sha256 928F68CB**（同样 594009 B、同样 74 页、同样 5 张图、同样 5 条 caption 文字）。两列并列：

| 产物 | 00-metrics.md（17:41:02 生成） | 我在 2026-11-21 18:03 重测 | 一致？ |
|---|---|---|---|
| main.pdf mtime | 2026-11-21 17:40:29 | **2026-11-21 17:53:40** | 否（晚 13 min，重编译过） |
| main.pdf sha256 前 8 | 378EED5F | **928F68CB** | 否 |
| main.pdf 字节 | 594009 | 594009 | 是 |
| main.pdf 页数 | 74 | 74 | 是 |
| main.tex mtime / sha | 17:33:45 / E72C9500 | 17:33:45 / E72C9500 | 是 |
| review_check | PASS fail=0 | PASS fail=0 | 是 |
| gauntlet | 16/16 PASS | 16/16 PASS | 是 |
| figfont min / median / violations | 4.73 / 7.97 / 0 | 4.73 / 7.97 / 0 | 是 |
| 五张图页码 | 4 / 10 / 10 / 14 / 15 | 4 / 10 / 10 / 14 / 15 | 是 |

**结论：PDF 字节数、页数、图页位置、五条 caption 文字、四条机器判据全部不变，只有编译时间戳与整包摘要变了（main.tex 未改）。** 因此本报告的所有判断对两个版本同时成立；但按 R-V11 必须并列，故上表两列都写。凡下文引用"PDF 页码"处，均指这两个版本共有的 4/10/10/14/15 页。

数据层时间线（2026-11-21，均为实测 mtime）：

| 产物 | mtime | 字节 | sha256 前 8 |
|---|---|---|---|
| figures/fig0_framework.pdf | 17:18:49 | 20174 | 8BE71EF1 |
| figures/fig1_p1_agreement.pdf | 17:18:50 | 18268 | A374766A |
| figures/fig2_p1_reliability.pdf | 17:18:50 | 22052 | F4B07835 |
| figures/fig3_p2_error.pdf | 17:18:50 | 17525 | 378C5E5D |
| figures/fig4_p2_voi.pdf | 17:18:51 | 15102 | 4BA378FA |
| data/alt_p2.json | 15:43:51 | 18432 | — |
| data/alt_p1.json | 16:33:16 | 744740 | — |
| data/alt_p3.json | 17:26:02 | 257695 | — |
| data/results_swc2026.json | 17:30:56 | 1164274 | — |

结论：**main.pdf（17:53:40）比所有 data/*.json 都新**，不存在"被测件落后 N 小时"。但有一件事必须写明：

1. `figures/*.pdf`（17:18:49–17:18:51）比 `data/alt_p3.json`（17:26:02）早 7 分钟、比 `data/results_swc2026.json`（17:30:56）早 12 分钟。核对 `code/alt_figures.py` 的读取清单：五张图只读 `alt_p1.json`（16:33:16）与 `alt_p2.json`（15:43:51），两者分别早于图 45 min 与 95 min，**不绘 alt_p3 / results_swc2026 的任何数**，因此图不是旧数据的产物，无需"落后 N 小时"警告。
2. `figures/` 目录 mtime 16:28:28 是目录元数据，不代表文件内容时间（文件 mtime 17:18 才是真值），不据此判陈旧。""")

# ---------------------------------------------------------------- §0.4 对账
put(72, 85, """### 0.4 与 `00-metrics.md` 的对账

| 项 | 00-metrics.md（17:41:02 生成） | 我在 2026-11-21 18:03 重跑 | 一致？ |
|---|---|---|---|
| review_check VERDICT | PASS (fail=0 unknown=0) | PASS (fail=0 unknown=0) | 一致 |
| main.pdf 页数 | 74 | 74 | 一致 |
| main.pdf mtime / sha | 17:40:29 / 378EED5F | **17:53:40 / 928F68CB** | **不一致，见 §0.5** |
| gauntlet | 16/16 PASS | 16/16 PASS | 一致 |
| R-V14 min / median | 4.73 / 7.97 pt | 4.73 / 7.97 pt | 一致 |
| R-V14 violations | 0 | 0 | 一致 |
| R-V14 single-char<6pt | 6 | 6 | 一致 |
| R-V06 claims | 51 exit=0 | 51 exit=0 | 一致 |
| R-V09 KNOWN OPEN | 1 pair `data\\alt_p3.json<-code\\make_alt_p3_md.py(0.03h)` | 同 | 一致 |

九项里八项一致，唯一的差异是 main.pdf 的编译时间戳与整包摘要（字节数、页数、图页位置全同），两列已并列于 §0.5。**R-V14 的 `min=4.73` 与图内实测的 4.34 pt 是两个口径，不是矛盾**，见 §3.0。""")

# ---------------------------------------------------------------- §0.2 verbatim
put(32, 54, """### 0.2 gauntlet_check.py — R 系列 16 项

```
> cd E:\\数学建模\\_swc2026\\SWC2026_C_ALT_BACKUP
> & "E:\\Mini\\envs\\mathmodel\\python.exe" "E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\gauntlet_check.py" .

[band] benchmark: ...\\refs\\official_standard.json  n=48  median sections=8.5
[PASS] paper resolved                      E:\\数学建模\\_swc2026\\SWC2026_C_ALT_BACKUP
[PASS] R-V01 body <= 30 pages              body=18 (header numerator of first Appendix A page)
[PASS] R-V02 single denominator            distinct totals=1
[PASS] R-V02 numbers contiguous            header numerators form 1..n with no gaps
[PASS] R-V03 zero CJK in body              body cjk=0 (appendix, not judged=0)
[PASS] R-V04 zero 'university'             hits=0
[PASS] R-V05 team number filled            KNOWN OPEN: \\baominghao placeholders must be filled before submission
[PASS] R-W06 no unsupported phrases        no <garbled>/<garbled>/obviously,
[PASS] R-W11 front matter order            ['summary', 'contents']
[PASS] R-W04 references have type markers  8 type markers on 8 entries
[PASS] R-W04 >=70% references cited        cite calls=8, [n] uses before bibliography=0, entries=8
[PASS] R-V06 verify_numbers present        claims=51 exit=0
[PASS] R-V09 no stale artefact             KNOWN OPEN (explain each): 1 pair(s): data\\alt_p3.json<-code\\make_alt_p3_md.py(0.03h)
[PASS] R-V07 band measured on both sides   figures/equations non-zero, so project was read from PDF text
[PASS] R-V07 out-of-band count             ABOVE=['words', 'abstract_numbers', 'abstract_density', 'distinct_numbers', 'pct_mentions', 'sections'] BELOW=['abstract_words']
[PASS] R-V14 figure text >= 6 pt           min=4.73 pt median=7.97 pt violations=0 single-char<6pt=6 (measured by python.exe)

16/16 PASS
```

（R-W06 行里的中文词在 PowerShell 控制台按 GBK 解码成了乱码，`00-metrics.md:46` 记的是原文 `no 众所周知/显而易见/obviously,`。判据本身 PASS，与 00-metrics 一致。另：脚本以 exit code 1 结束，原因是 `pdftotext: security risk: running with elevated privileges` 这一行落到了 stderr 并被 PowerShell 当成 NativeCommandError —— 判据输出本身是 16/16 PASS，`00-metrics.md:35` 记 `exit=0` 是在没有该 stderr 干扰的环境下取的。）""")

# ---------------------------------------------------------------- §0.1 verbatim
put(14, 30, """```
> cd E:\\数学建模\\_swc2026\\SWC2026_C_ALT_BACKUP
> & "E:\\Mini\\envs\\mathmodel\\python.exe" "E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\review_check.py" .

paper: .
pdf: main.pdf   pages: 74
[ OK ] C4    p1 has summary/abstract=True
[ OK ] C4    p2 has contents/directory=False
[ OK ] C5    header lines matched=72
[ OK ] C5    headers leaking identity=0
[ OK ] C7    chinese chars in body=0 (appendix, not judged=0)
[ OK ] C6    total pages=74
[ OK ] C9    appendix=True code=True
[ OK ] C11   placeholder team number hits=0
[ OK ] C11   self-declared invalid identifier in body=0
[ OK ] C11   has References section=True
[ OK ] C8    reference type markers=8

VERDICT: PASS  (fail=0 unknown=0)
```

与 `00-metrics.md:18-32` 逐字一致。注：`[ OK ] C4 p2 has contents/directory=False` 是 C4 的目录项判据，值为 False（次页无目录）；该项判 OK 是因为 C4 只要求首页有摘要，目录缺失在本判据下不扣分 —— 这条留给 `01-compliance` 判，本报告不重复。""")

out = '\n'.join(lines)
out = out.rstrip('\n') + '\n'
# fix BYTES line
body = out.encode('utf-8')
# compute final byte count with the BYTES line itself counted
import re
placeholder = 'BYTES ' + '0' * 12
tmp = re.sub(r'^BYTES \d+', placeholder, out, count=1)
n = len(tmp.encode('utf-8'))
out2 = re.sub(r'^BYTES \d+', 'BYTES %d' % n, out, count=1)
# if digit count differs from placeholder, re-fix
n2 = len(out2.encode('utf-8'))
if n2 != n:
    out2 = re.sub(r'^BYTES \d+', 'BYTES %d' % n2, out2, count=1)
    n3 = len(out2.encode('utf-8'))
    if n3 != n2:
        out2 = re.sub(r'^BYTES \d+', 'BYTES %d' % n3, out2, count=1)
P.write_bytes(out2.encode('utf-8'))
print('lines after:', len(out2.split('\n')))
print('bytes:', len(out2.encode('utf-8')))
print('L1:', repr(out2.split('\n')[0]))
print('last:', repr(out2.split('\n')[-2]))
print('BOM:', P.read_bytes()[:3])
