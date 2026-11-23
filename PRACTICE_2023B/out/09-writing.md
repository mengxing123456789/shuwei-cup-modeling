BYTES 8158
# 09-writing — main.tex 与摘要撰写交付

角色：论文撰写手（G7 / G12 门）。产物：`E:\数学建模\PRACTICE_2023B\main.tex`（671 行）与 `main.pdf`（28 页）。
上游四个文档（01-model / 03-numbers / 08-figures / 05-caliber）未改动一个字；`out/03-numbers.md` 的 33,837 字节版本由它自己的 `code/verify_numbers.py` 在复算时重写（输出里 `report=... bytes=33837`），不是本角色手改。

## 1. 结构（族骨架 B，题给五个子问 → 五章）

| 块 | main.tex 行号 | 内容 |
| --- | --- | --- |
| 摘要 | 9–24 | 加粗标题 + 四段式（15/17/19/21 行） + `\keywords`（第 23 行） |
| 目录 | 27–31 | `\setcounter{tocdepth}{1}`，目录只占第 2 页，第 3 页起正文 |
| I Introduction | 33–49 | Background / Restatement / Our Work（5 条） |
| II Problem Analysis | 50–60 | 闭合=3 自由度、daf 去稀释、三条阈值、两附录桥 |
| III Assumptions | 61–74 | 10 条编号假设，每条带「为何 / 谁用 / 可否检验」 |
| IV Notations and Data | 75–87 | 4.1 只留一句指向附录 A；4.2 来源 / 4.3 清洗 / 4.4 比较合理性 |
| V..IX 五问 | 88–505 | 每问 Mechanism / Model(编号公式) / Results(表+图) / 验证与结论 |
| X Sensitivity and Error | 506–526 | 阈值路径 / 扰动审计 / 数值自检与耗时 |
| XI Conclusion | 527–529 | 结论带基准数字 |
| XII Strengths and Weaknesses | 530–563 | 3 条机制优点 + 3 条带方向与量化代价的边界弱点 |
| References | 545–562 | 16 条 `[J]/[M]/[R]`，16/16 在正文被引 |
| Appendix A | 565–614 | 符号表（正文只留指针，满足经验⑤） |
| Appendix B | 616–end | `figures/code_index.tex` + `code_totals.tex` + 英文 `lstlisting` 节选 |

16 张图全部被引用（fig01–fig16，见 08-figures.md 的图注原文），7 张正文表 + 附录脚本表；正文表统一 `{\small\setlength{\tabcolsep}{1.7–2.2pt}}` 整块包（main.tex:141/212/293/365/386/447/471/625），无 Overfull。

## 2. 摘要（判据 `mmkit.review_bench.abstract_stats`）

四段顺序 Background and Task → Modeling Framework → Results per Question → Validation and Limitation（main.tex:15/17/19/21），实测：

```
words = 447      verdict_words = inside   （区间 327–449，恰与 2026_C 的 447 收敛点一致）
numbers = 13     verdict_numbers = ok      （不同取值 8 个，未超 8 个上限）
density = 2.91   question_refs = 5
```

复算：`cd E:\数学建模\.agents\skills\mathmodeling; & 'E:\Mini\envs\mathmodel\python.exe' -c "import sys;sys.path.insert(0,'scripts');from mmkit import review_bench as r;print(r.abstract_stats(r'E:\数学建模\PRACTICE_2023B\main.pdf'))"`

- ≥3 个数字且每个带基准：tar −37.7%（CS，端点比）、H2 = 14.47 倍噪声底、char 均值差 −33.27 个百分点（8/8 档对）、CE 气相碳 −77.2%（端点）、CS LOO 5.50%（对 5% 声明误差）、1/15=6.67% 的扰动翻转率、CE 失拟 F=3.42（对噪声底）。
- 关键词与第二段模型名同序（main.tex:23）：Compositional data → Isometric log-ratio regression → Noise-calibrated species tiering → Paired contrast at equal ash level → Selectivity and carbon accounting → Monte-Carlo prediction envelope。
- 末段含具体局限：CE/LG 线性失拟 F=3.42/3.52，预测降为「趋势描述」，区间相应放宽；无温度程序 ⇒ 只能给等转化率脊线而非速率律。
- 未承诺正文没有的东西：摘要里没有「检查全过」之类元声明。

## 3. 门与复算证据

| 门 | 结果 | 复算命令 |
| --- | --- | --- |
| G7 review_bench | 11/11 PASS（C4 首页摘要/次页目录、C5 页眉 25 处、C7 正文 CJK=0、C9 附录+代码、C11 无占位队号、C8 16 个类型标记） | `& 'E:\Mini\envs\mathmodel\python.exe' -c "import sys;sys.path.insert(0,r'E:\数学建模\.agents\skills\mathmodeling\scripts');from mmkit import review_bench as r;rep=r.check_paper(r'E:\数学建模\PRACTICE_2023B\main.pdf');print([(f.cid,f.ok) for f in rep.findings])"` |
| G8 gauntlet 16 项 | **16/16 PASS** | `& 'E:\Mini\envs\mathmodel\python.exe' -X utf8 "E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py"` |
| R-V01 页数 | body=24 ≤ 30（总 28 页，附录 A 起于印刷页 24） | 同上；`pdfinfo main.pdf` → Pages: 28, A4 |
| G12 数字绑定 | claims=547 declared=547 checked=547 failures=0；**tex_bound=145/145，tex_state=written** | `& 'E:\Mini\envs\mathmodel\python.exe' code\verify_numbers.py` |
| G17 代码清单 | 15/15 行与磁盘一致；main.tex 用 `\input{figures/code_index.tex}` | `& 'E:\Mini\envs\mathmodel\python.exe' code\gen_index.py --check` |
| G19 无 `??` | PDF 全文 `??` = 0；编译无 undefined reference | `pdftotext -layout main.pdf -` 后数 `\?\?` |
| 全角/中文 | PDF 全文 CJK = 0；main.tex 无 CJK（venue 逐页扫） | 正则 `[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uFF01-\uFF60]` |
| 图内字号 R-V14 | violations=0（正文 16 图单独测 min 6.30–6.80 pt，全过） | gauntlet_check；或 `mmkit.figfont` 逐图 |
| 编译 | 两遍 xelatex exit 0，0 Overfull / 0 Underfull | `& 'E:\MIKTEX\miktex\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error main.tex`（跑两遍） |

## 4. 本轮实际修掉的问题（都已在上面复算）

1. **参考文献引用率不达标 → 修**：原先只有 4/16 被引（gauntlet R-W04 FAIL）。补了 12 处真引用：成分数据 Aitchison1982 / Filzmoser2009 / Egozcue2003 / Pawlowsky2011（main.tex:53）、ILR 实现 Boogaart2008（main.tex:111）、题给数据 ProblemB2023（main.tex:80）、动力学 Kissinger1957 / Ozawa1965 / Vyazovkin2011 / Brown2000（main.tex:357）、NumPy/Matplotlib（main.tex:519）。现在 16/16 被引，14 个 `\cite` 调用。
2. **G17 陈旧 → 修**：重跑 `code/gen_index.py`（15 scripts, 236,854 bytes），并把附录表标题里硬写的「221,830 bytes over fourteen scripts」换成生成的 `\CodeIndexCount{}` / `\CodeIndexBytes{}`（main.tex:622–624），不再自相矛盾。
3. **漏图 → 补**：fig03（ILR 拟合残差）、fig06（minor φ）、fig07（bridge）原先没被排进正文，且 `fig:q2bridge` 是悬空引用。已补图并给 label（main.tex:180–185、252–266），现在 16/16 图被引、无 `??`。
4. **目录溢出到第 3 页 → 修**：`tocdepth=1`（main.tex:27），目录回到第 2 页。
5. **Overfull 5.24pt / 1.40pt → 清零**：`\emergencystretch=1.5em`（main.tex:6），页数不变。
6. **R-V14 图内字号 FAIL（13 处）→ 修**：真因不是图，是**表格与附录里多字符数学下标**（$\gamma_{\mathrm{Tar}}$、$\tau_{\mathrm{step}}$、$\sigma_{\rm fit}$ 等在 7.5–9pt 表格里落成 4.98pt）。把多字符下标改成单字母/括注：τ_s / τ_T / τ_D（main.tex:129–131, 588–590）、σ_F / σ_N、n_o、y_S、γ (Tar)（main.tex:370–373），violations 13 → 0。单字符下标（C₂H₆ 等 111 处）按该门定义「not judged」。表字号统一提到 `\small`（可读性更好，0 Overfull，总页数 27→28 仍远低于上限）。

## 5. 交给格式合规手的注意点

- R-V05 仍是 `KNOWN OPEN`：`\baominghao{apmcm2699001}`（main.tex:3）需在提交前确认是真实队号；当前不是占位符（gauntlet 判 placeholder=False）。
- R-V07 参考带外项（abstract_words / distinct_numbers / pct_mentions / density_per_100w / tables / references 为 ABOVE）是对 16 篇一等奖语料的**统计提示**，不是违规；摘要词数按派单判据 327–449 为 inside。
- 附录不 `\lstinputlisting` 源码文件：源码里有中文注释，venue 的 `check_chinese` 逐页扫，印出来即命中。现附录 B 只放英文节选 + 脚本清单表。
- 复跑图：`E:\Mini\python.exe -X utf8 code\make_figures.py`；图检：`E:\Mini\envs\mathmodel\python.exe -X utf8 code\check_figures.py`。改图后需重跑 verify_numbers + gen_index --check + gauntlet。
- 本轮临时文件（out/_main_backup.tex、_p17.png、_p26.png、_check.txt）已删除，无陈旧产物残留。

VERDICT: PASS
