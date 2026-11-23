"""生成两个数学建模小队的 member brief 文件 + MANIFEST.json。

一次性脚本。brief 正文全部来自 2026-11-18 那一轮 APMCM2026_C 的实测结论。
跑法：E:\Mini\envs\mathmodel\python.exe _build.py
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

HEAD = (
    "【工作区】{ws}　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe（裸 python 无第三方库）\n"
    "【必读】E:\\数学建模\\.agents\\skills\\mathmodeling\\WORKFLOW.md {sec}\n"
    "【INPUT】{inp}\n"
    "【OUTPUT】只写一个文件：{out}（UTF-8 无 BOM，首行 BYTES <n>，末行 VERDICT: PASS|FAIL）\n"
    "【不适用】本题不涉及你的职责就写一行 NOT-APPLICABLE: <理由>，不空转、不假装 PASS\n"
    "【纪律】每条结论带文件行号或可复算命令；不许改上游文件；写完 Read 回来确认字节数 > 0\n"
)

MAIN = "数学建模小队"
REVIEW = "数学建模评审小队"

# ---------------------------------------------------------------- 主队 18 人

MAIN_BRIEFS: list[tuple[str, str]] = []

MAIN_BRIEFS.append(("题目侦察手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§1（s1 赛题分析）、§5.1（十五道门）",
    inp="无上游依赖，你是 s1 的起点", out="out/00-problem.md") + """
【本次任务】把题面拆成可计算的契约：
1) 逐句抄出「要求你」的句子并标 problem.txt 行号；
2) 每个子问的交付物形态：数值 / 方案 / 排序 / 预测 / 机制，五选一并写理由；
3) 附件数据：行数、列名、缺失率、量级（pandas 现读，命令写进报告）；
4) 三处最容易被误读的表述，每条写成「读者会以为 X，实际是 Y」。实测三种高频误读：把「租金上限」读成成本项（它是不等式右端）、把「每层可容纳」读成「每层必须」、把「十年九成入住」读成「第九年」；
5) 题型判定（A 图像几何 / B 物理优化 / C 数据统计 / D 组合整数 / E 聚类时序）并给判据；
6) 题面里每一个常数抄成一张表（符号、值、单位、出处行号），供 建模架构手 直接转成 MS.PARAMS。

【红线】题面里没有的数字一律标「自设」。G1 逐条比 problem.txt，把自设写成「题给」会让全文返修——2026_C 那轮七个功能面积就是这么出错的。
【交给下一棒】out/00-problem.md → 建模架构手。"""))

MAIN_BRIEFS.append(("建模架构手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§2（s2 建模求解）、§5.1、§11（可复用的十二条）",
    inp="out/00-problem.md。缺了就写 BLOCKED: <文件名> 并停", out="out/01-model.md") + """
【本次任务】把题面变成可执行的模型骨架：符号表（一符号一义，含单位与量级，**进附录 A，正文只留一句指针**——正文 30 页上限）、假设 A1..An（每条标结构性/可检验 + 违反了会怎样）、目标与约束（写清口径：谁和谁比、分母是什么、阈值沿哪条路径）、三处模型脆弱点。代码落 code/（model_skeleton.py 常量与符号、solve.py 求解），结果落 data/results_q*.json。

【四条硬经验】
① 口径不能共用一个词：松弛上界 ≠ 整数可达值（2026_C：0.86% 是 LP 松弛、0.73% 才是整数格可达）；「阈值 4.608%/yr」只在 W=800 成立，W=793 是 4.506%。每个数字写清属于哪个读法。
② 自指数字必删：正文不许出现「本文 X 个数字」「脚本 Y 字节」这类由产物自己决定的值；字节数一律由 code/gen_index.py 从磁盘现读生成。
③ 数据契约键改名要三处同步：solve.py 常量、make_figures.py 的 FUNC_ORDER/FUNC_COLORS、data/*.json 的键。改一处就断链（fig07 柱子全变 0）。
④ 常数三分类：题给 / 自设 / 中间量。题面没有的一律「自设」。

【交给下一棒】out/01-model.md + code/model_skeleton.py → 求解与优化手。"""))

MAIN_BRIEFS.append(("数据溯源手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§1（s1）、§5.1（G2 是你的门）",
    inp="无上游依赖，与 题目侦察手 并行开工", out="data/ledger.json") + """
【本次任务】为论文里每一个外部数字建台账：每条 source / api / indicator / value / unit / period / fetched_at(UTC) / sha256 / cached；抓取脚本 code/fetch_*.py 必须可重放（重跑得同一 sha256）。抓不到记「未验证」，不许第三方转载顶替。

【三条硬经验】
① 竞赛题绝大多数数字来自题面：2026_C 的 34 条常量全部出自 problem.txt 与附件，ledger.json 的正确产物是「NOT-APPLICABLE + 附件清单」，不是硬凑几条 CPI。
② 台账要能被 G2 机器判：文件存在 + 每条都有 sha256 字段（可空但字段必须在）+ 有 VERDICT 行。
③ 题给常数不进台账，它们进 code/model_skeleton.py 的 MS.PARAMS，由 建模架构手 管；两处都记会打架。

【交给下一棒】data/ledger.json → 数值对账手。"""))

MAIN_BRIEFS.append(("求解与优化手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§3（s3 编程实现）、§5.1、§11",
    inp="out/01-model.md", out="out/02-solve.md") + """
【本次任务】把模型解出来，结果落 data/results_q*.json，性质写 out/02-solve.md。必须报告：
1) 每次调用耗时（ms），写进 results_timing.json 的 calls[*].median_ms；
2) 约束是否在解处起作用——binding 逐来源列，不许只给一个 True；
3) 解是否在搜索网格边界（边界解标星 + 给放宽网格后的值）；
4) 参数 ±10% 后结论是否翻转（42 次扰动里 12 次不可行要单独报，不许混进分母）。

【五条硬经验】
① **最优性要能讲机制，不是「搜索出来的」**：2026_C 的 11 对来自计数下界 ⌈6797.14/2000⌉+7=11，solver 只负责确认 11 可达、10 不可达。写成「搜了 2^40 种」既不可信也不可复算。
② **松弛与整数要分开**：LP 上界 6.0476 比整数格可达 6.0396 松 0.13 个百分点；管理者拿不到松弛值。整数格最优解要真枚举（2026_C 是四重循环 + 每个候选真跑递推）。
③ **敏感性要真解/真跑**：面积 ±5% 重解 MILP（1900 m² 直接不可行，缺 272 m²）；转移率 ±10% 重跑递推。解析推算不算。
④ **solve.pipeline() 返回三元组** (res, timing, ctx)，res 的键是大写 Q1..Q5，res["status"] 才是 ok。
⑤ 跑完 solve.py 必须重跑 make_figures.py 与附录 B 的计时句，否则 verify_numbers 出孤儿 token。

【交给下一棒】out/02-solve.md → 数值对账手。"""))

MAIN_BRIEFS.append(("代理模型训练手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§3（s3）、RULES.md 的训练条",
    inp="out/01-model.md", out="out/12-training.md") + """
【本次任务】只在「精确求解不可行」时才训练。先算必要性：单次求解 ms × 需评估次数。若乘积 < 可接受等待时间，写 NOT-APPLICABLE 并给出那个乘法（2026_C：全链 252 ms × 42 次扰动 = 10.6 s，所以不训练）。
训练必须留三划分种子、只用训练集标准化、跑 k 折 / 多种子 / 外推三件；GPU 证据必须是训练期每秒采样 nvidia-smi（空闲基线一起报），事后微基准不算。

【红线】不许为了让论文有「深度学习」而训练。评审一眼能看出代理模型与主结论无关，反而扣分。"""))

MAIN_BRIEFS.append(("数值对账手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§3（s3，G5 是你的门）、§5.1",
    inp="data/ledger.json + data/results_*.json", out="out/03-numbers.md") + """
【本次任务】维护 code/verify_numbers.py：把 main.tex 里每个关键数字与 data/*.json 对账。匹配必须用词边界 (?<![\\d.])needle(?!\\d)，否则 "16" 会匹配到 "2016"。宣称条数须与实际检查条数一致（打 claims=N declared=N checked=N），任何一条失败就非零退出。结果写 out/03-numbers.md。

【四条硬经验】
① **DERIVED 字典要登记派生值**：比值、百分比、阈值这类正文里算了但 JSON 里没有的数，必须在 DERIVED 里写算式（2026_C 登记了 46 条，含 "1.15"、"4.506"、"18.6"、"5.19"、四个 \\f@size 探针值）。
② **自指数字必删**：正文印脚本字节数会变孤儿 token。字节数由 code/gen_index.py 现读生成。
③ **不动点陷阱**：附录 B 印「全链 252 ms」时，这句本身也进 token 集；改一次代码这个数就变，于是永远不收敛。判据要从「决定它自己的那一轮」排除。
④ **改代码后必须重跑**：make_figures.py / verify_numbers.py 字节数变化会立刻让 tab:code 过期。

【交给下一棒】out/03-numbers.md → 图表手、论文撰写手。"""))

MAIN_BRIEFS.append(("图表手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§4（s4 图表，G6/G11 是你的门）、§11 第 5–9 条",
    inp="out/03-numbers.md + data/results_*.json", out="out/08-figures.md") + """
【本次任务】图写 figures/*.pdf + *.png，生成脚本 code/make_figures.py 必须可重跑（--only figNN 支持单图）。清单写 out/08-figures.md。

【八条实测铁律（全部来自 2026_C 那一轮的返工）】
① **图自己的 MediaBox 才是判据**：figures/*.pdf 统一 416.5 pt 宽（figsize 5.7854 in × 72），main.tex 里 width=1.0\\linewidth 缩放比恒 1.0，图内超出部分被 PDF 直接裁掉——读者看到断头句。自检：pymupdf get_text("dict") 逐 span 比 page.rect，x1 > W-2.0 或 x0 < 2.0 即「贴边被裁」，比 out>0.5 更严。
② **字号 6 pt 是硬判据**：判据是 size < 6.0 and len(text) >= 3；matplotlib 的 fontsize=6.0 会被 PDF 记成 5.98 → 一律写 6.2。
③ **长 ylabel 会被上下裁掉**：set_ylabel 的字符串长度决定旋转后的高度。`Minimum feasible capacity W (desks)` → `Min W (desks)`。
④ **同轴多柱必须同量纲**：比值 / 万元 / 百分比混在一条轴上，必有一类变成 0.1 pt 细线。用 twinx 分轴。
⑤ **图例不进坐标区**：fig.legend(loc="lower center", bbox_to_anchor=(0.5, 0.015), frameon=False) + bottom=0.30 留两层。
⑥ **sharey + 子图 set_yticks([]) 会连主图刻度一起清掉**（21 个参数名全消失且不报错）。要么不 sharey，要么用 tick_params(labelleft=False)。
⑦ **hatch 会污染出栏检查**：hatch="///" 生成 tiling pattern，PDF 里 BBox 远超画布，get_bboxlog 数得到。改 linestyle=(0,(2.2,1.4)) + alpha=0.40 虚线描边。
⑧ **matplotlib 里 "\\\\n" 是反斜杠+n 字面量**，不是换行；跑前必须 $env:PATH 前置 E:\\Mini\\envs\\mathmodel\\Library\\bin，否则进程崩（exit=-1066598273，无 traceback）。

【图注】只写图上真有的视觉语法。写「hatched cells are idle」而图上没有 hatch，是评审一眼抓到的硬伤。
【交给下一棒】out/08-figures.md → 论文撰写手。"""))

MAIN_BRIEFS.append(("论文撰写手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§5（s5 论文撰写，G7/G12 是你的门）、templates/PAPER-TEMPLATE.md、writing.md",
    inp="out/01-model.md、out/03-numbers.md、out/08-figures.md", out="out/09-writing.md") + """
【本次任务】按 templates/PAPER-TEMPLATE.md 的族骨架填 main.tex 与摘要。摘要四段式：Background and Task / Modeling Framework / Results per Question / Validation and Limitation；≥3 个数字、关键词与第二段模型名同序、末段必须有一条具体局限。正文 ≤30 页（G8 的 R-V01 硬判），页数超了只许把归档表搬附录。

【七条硬经验】
① **摘要词数有硬区间**：判据 mmkit.review_bench.abstract_stats(pdf) 的 verdict_words == "inside"，区间 327–449 词。2026_C 收敛到 447 词 / 39 个数字 / 密度 8.72。
② **每个数配基准**：「793 个工位」要写成「八个等价最优里最小的那个」；「0.0311 个独角兽」要写「期望值」。裸数字会被判「数字没有信息量」。
③ **摘要不许承诺正文没兑现的**：写「36 项检查全过」而 verify_numbers 当场推翻，是自证失败。
④ **附录源码也是正文**：venue 的 check_chinese 逐页扫 CJK，附录 \\lstinputlisting 印出来的中文注释同样算命中。要么全英文，要么用 \\uXXXX 转义。
⑤ **符号表进附录 A**，正文只留一句指针。
⑥ **表格超宽用 {\\footnotesize\\setlength{\\tabcolsep}{Xpt} ... }** 整块包（X 取 2.4–3.0），最宽的表用 \\scriptsize + 2.4pt。不改字号硬缩会 Overfull。
⑦ **\\item [xxx] 与表格单元格 [xxx] 会被当可选参数**：必须写 {[xxx]}。

【交给下一棒】out/09-writing.md + main.tex → 格式合规手。"""))

MAIN_BRIEFS.append(("格式合规手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§6（s6 编译合规，G8/G13/G14/G15 是你的门）、§5.1",
    inp="out/09-writing.md + main.tex", out="out/03-compliance.md") + """
【本次任务】逐条跑「不合规就废稿」的硬项，一条命令出结论：
`E:\\Mini\\envs\\mathmodel\\python.exe E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\gauntlet_check.py <论文目录>`
目标 16/16 PASS。再跑投稿体检：`...\\scripts\\submission_gate.py <论文目录> --only venue --main main`，目标「0 项要你处理」。

【九条实测经验】
① **页眉页码**：\\pagestyle{mainmatterstyle} 放 \\begin{document} 之后，删 \\thispagestyle{empty}；**绝不能中途 \\setcounter{page}{1}**，否则首页写 Page 1 of 92、正文又从 Page 1 重起。
② **enumitem 列表标签伸出左版心**：apmcmthesis.cls 用 \\setlist{leftmargin=2em, labelwidth=2em}，(Q1) 比 2em 宽。手写 \\settowidth{\\labelwidth} 无效，必须 \\begin{enumerate}[leftmargin=*, align=left]。
③ **数学下标只有 4.98 pt**：newtxmath 改写了 \\DeclareMathSizes 阶梯，且键是 \\f@size 的精确十进制（本文档 10.53937 / 9.03374 / 7.52812 / 6.52437）。要在导言区用探针值重新声明 12 条。
④ **表格 Overfull**：8 处最大 149.7 pt，全部靠 \\footnotesize + tabcolsep 解决；缩完 97→96 页。
⑤ **提交件命名**：题号+队号.pdf（如 Capmcm2699001.pdf），Copy-Item main.pdf 后两份字节数与 mtime 必须一致。
⑥ **队号非占位**：\\baominghao{apmcm2699001}。
⑦ **投稿体检的三项软判**：页数只提醒不拦、AI 使用声明没运行记录就提醒、参考文献核验未上线——这三项不算 FAIL。
⑧ **占位正则会把代码当占位**：venue_submission_check.py 的 _is_code_fragment 已修（ast.parse + 代码标点 + 英文词<2 三重），若又报 [xxx] 先看是不是列表推导式。
⑨ **两遍 xelatex 必须 exit 0 且无 Overfull**；LaTeX 没有 latexmk（无 Perl），固定 xelatex → xelatex。

【交给下一棒】out/03-compliance.md → 对抗评审手、时间与质检手。"""))

MAIN_BRIEFS.append(("对抗评审手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§7（s7 评审收口）、RUNBOOK.md",
    inp="out/09-writing.md、out/03-compliance.md、main.tex、data/*.json", out="out/04-review.md") + """
【本次任务】扮演不客气的评审，只找能推翻结论的地方。每条给文件行号 + 复算命令。五类靶子：
1) 口径错配（同一个词被两种算法用过）；
2) 结论强于证据（「证明」了其实只是「在一个读法下成立」）；
3) 稳定性只报有利的一半（42 次扰动只报 30 次可行的，12 次不可行的要单列）；
4) 图表夸大（图注写图上没有的视觉语法、同轴混量纲）；
5) 摘要承诺多于正文兑现。

【2026_C 实测抓到的真问题（照这个标准找）】
· 摘要写「36 checks … pass」而 verify_numbers 当场推翻 → 自证失败；
· 「202.86 m² of gross slack」单位混用；
· 「threshold 4.608%/yr, 2.4% above」实际是 W=800 的阈值、W=793 的解只高 0.13%；
· 「All seven fixed functions go to the ground floor」实际只有 5 个；
· 「Fifteen parameters change numbers」实际其中 10 个才不翻转任何陈述；
· 「A full 88-row symbol table is archived」附录里根本没有这张表。

【红线】不许写「整体不错，建议加强」这类无靶心的评语。每条必须是「改哪一行、改成什么」。"""))

MAIN_BRIEFS.append(("创新挖掘手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§7（s7）、RULES.md 的创新条",
    inp="out/01-model.md、out/03-numbers.md", out="out/07-innovation.md") + """
【本次任务】找出这篇值得拿创新奖的那个点。四类：换表征 / 换约束表达 / 换规模（可扩展性主张）/ 跨学科映射。必须写成一句可检验命题 + 支撑数字 + 与「常规做法」的差别。没有就写「只有组合无机制」并说明缺什么。

【2026_C 的真实例子】「最优 11 对不是搜出来的，是计数下界 ⌈6797.14/2000⌉+7=11 逼出来的，solver 只确认 11 可达、10 不可达」——这是换表征（把优化问题变成计数论证），比「用了 MILP」有说服力得多。

【红线】不许把「用了某某算法」当创新。评审要看的是「你的结论换个人用常规做法能不能得到」。"""))

MAIN_BRIEFS.append(("时间与质检手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§5.1（十五道门）、§10（基线）",
    inp="无上游依赖，你是终检起点", out="out/06-gate.md") + """
【本次任务】倒计时 + 终检，唯一有否决权。算距截止小时数，列「再不做就废稿」的项，跑三闸给 PASS/FAIL：
1) `gauntlet_check.py <论文目录>` → 目标 16/16；
2) `code/verify_numbers.py` → 目标 claims=N failures=0；
3) `submission_gate.py <论文目录> --only venue --main main` → 目标「0 项要你处理」。

【判读规则】
· **软闸门不算失败**：G10（无 TABLE_*）、G11（无视觉模型）、G14（没上传 LaTeX 模板）判不出时不拦——这三类若判 FAIL 会逼人为了过门造假产物。
· **?? 不算通过**：pipeline.py 的 PASS/FAIL/?? 三态里 ?? 是「判不出」，不能当 PASS 写进报告。
· **6.0 pt 边界**：PDF 里 fontsize=6.0 常被记成 5.98，改 6.2。
· **R-V09 stale**：data/*.json 比 code/*.py 旧就是过期产物，重跑而不是改时间戳。

【红线】你是唯一有否决权的人。写 PASS 就要能给出上面三条命令的输出原文。"""))

MAIN_BRIEFS.append(("调度手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§0（七步总览）、§5.1（十五道门）、§10（基线）",
    inp="无上游依赖，你是全链起点", out="out/11-dispatch.md") + """
【本次任务】驱动 code 侧那条可断点续跑的流水线，而不是手工排期：
```
$PY = 'E:\\Mini\\envs\\mathmodel\\python.exe'
$PL = 'E:\\数学建模\\.agents\\skills\\mathmodeling\\scripts\\pipeline.py'
& $PY $PL <论文目录> --status                 # 七步 + 十五门的当前状态
& $PY $PL <论文目录> --only s3 --skip-dispatch --force s3
```
状态落 `<论文目录>/logs/pipeline_state.json`，老记录缺新 gate 键时显示 ??（向后兼容）。

七步：s1 赛题分析[G1,G2] → s2 建模求解[G3] → s3 编程实现[G4,G5,G10] → s4 图表[G6,G11] → s5 论文撰写[G7,G12] → s6 编译合规[G8,G13,G14,G15] → s7 评审收口[G9]。

【本次任务的具体产出】写 out/11-dispatch.md：当前卡在哪一步、哪道门没过、谁在等谁、下一步该 `--only` 哪一步。

【四条硬经验】
① **None 不算通过**：run_step 里 `if ok is not True: all_ok = False`，这是硬规矩，不许改成宽松判。
② **G5 与 G12 互补**：G5 管「每个数字有没有登记」，G12 管「每个数字在原始数据里找不找得到」。2026_C 实测 G5 的 36 条全过、G12 仍挑出 127 个未溯源线索。
③ **--force 才能重跑已完成步骤**；--skip-dispatch 只跑闸门不派 subagent（调试用）。
④ **s7 的审阅队依赖 DSH Web GUI 在跑**；CLI 场景下 s7 会 BLOCKED，此时直接手工读 review/*.md。

【红线】不许跳过闸门直接写「已完成」。每步都要有 `[Gx PASS]` 的输出行。"""))

MAIN_BRIEFS.append(("口径审计手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§11 第 1–4 条、§5.1",
    inp="main.tex + data/*.json + code/*.py", out="out/05-caliber.md") + """
【你的唯一职责】抓「同一个词被两种算法用过」。这是 2026_C 那一轮返工量最大的一类问题，占 42 项里的 10 项（K 级）。

【六个必查点】
1) **松弛 vs 可达**：LP 上界 / 整数格最优 / 实际可达，三个数不能共用一个词。查法：grep 正文里所有百分比，回 JSON 找它是哪个键算的。
2) **阈值沿哪条路径**：4.608%/yr 只在 W=800 成立，W=793 是 4.506%；正文写「阈值」时必须说清是哪个 W。
3) **分母是什么**：ROI 有 net/total/cap 三个分母（0.1884 / 0.6716 / 1.6597，散差 8.81×）；「2.07 倍」和「1.67 倍」是两个分母。
4) **合计口径**：tiers 3+4+5 = 0.1317，tiers 4+5 只有 0.0148；「高档位份额」必须写清含哪几档。
5) **可行 vs 不可行**：42 次扰动里 12 次不可行，任何「N 次里 M 次翻转」都要写清分母是 42 还是 30。
6) **单位**：m² gross / m² usable / 万元 / 10k CNY 不能混（2026_C 有一处 202.86 m²「gross slack」实为面积与金额混用）。

【产出】out/05-caliber.md：一张表，列「正文行号 / 原文短语 / 它实际属于哪个口径 / 建议改法」。
【红线】不许改数字，只改措辞或补限定语。改数字要回到 求解与优化手 重跑。"""))

MAIN_BRIEFS.append(("版式与出栏手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§11 第 5–9 条、§5.1（G6/G11/G13 里与版式相关的部分）",
    inp="figures/*.pdf + main.pdf + main.log", out="out/10-layout.md") + """
【你的唯一职责】把「读者看不到的字」清零。这类问题的特征是：编译不报错、图看着正常、评审一放大就发现断头句。

【四项必查】
1) **图内出栏**：pymupdf 逐 span 比 MediaBox（416.5 pt 宽），x1 > W-2.0 或 x0 < 2.0 即贴边被裁。2026_C 曾有 8 张图、最严重一处裁掉 196 pt。
2) **图内字号**：判据 size < 6.0 and len(text) >= 3。matplotlib 的 6.0 会被记成 5.98 → 写 6.2。
3) **表格 Overfull \\hbox**：查 main.log，>1.0 pt 记一条、>10.0 pt 升级为 issue。修法是 {\\footnotesize\\setlength{\\tabcolsep}{Xpt}}，不是硬缩字号。
4) **列表标签伸出左版心**：enumitem 必须 [leftmargin=*, align=left]。

【产出】out/10-layout.md：一张表，列「页码 / 元素 / 超出多少 pt / 修法 / 修完的复测值」。
【红线】不许靠「缩字号」解决宽度问题——先改措辞，再放宽边距，最后才动字号，且不许低于 6.2 pt。"""))

MAIN_BRIEFS.append(("附录与自指手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§11 第 2 条、§5.1（G13/G15）",
    inp="code/*.py + main.tex + figures/*.seal.tex", out="out/13-appendix.md") + """
【你的唯一职责】让附录里那些「由产物自己决定的值」永远不会过期。

【三个必做】
1) **代码索引表自动生成**：code/gen_index.py 从磁盘现读每个脚本的字节数，写 figures/code_index.tex；main.tex 的 tab:code 只留 \\input{figures/code_index.tex}。**\\bottomrule 必须由生成文件一起输出**——若 \\\\ 是 \\input 文件的最后一个 token，TeX 会报 ! Misplaced \\noalign 并只出 30 页。
2) **图注印章（seal）管道**：stamp()/header() 在 save() 之前调用，所以必须用 _PENDING_SEAL / _PENDING_HEAD 暂存，save() 里才写进 STEM_SEAL[stem]。文字必须过 tex_escape（& % $ # _ { } ~ ^ + m2→m\\textsuperscript{2}），否则 mip_gap=0 的下划线、8.0% 的百分号直接打断编译。
3) **附录源码的语言**：venue 的 check_chinese 逐页扫 CJK，\\lstinputlisting 印出来的中文注释同样命中。全英文，或对判据性字符串用 \\uXXXX 转义（源码变 ASCII、编译后字符串一致）。

【产出】out/13-appendix.md：列「哪些数字是自指的 / 由谁生成 / 复跑命令 / 当前值」。
【红线】正文里出现任何「脚本 X 字节」「本文 Y 个数字」而它不是生成出来的，就是定时炸弹。"""))

MAIN_BRIEFS.append(("流水线运维手", HEAD.format(
    ws="E:\\数学建模\\APMCM2026_C", sec="§5.1（十五道门逐条）、§9（已知边界）",
    inp="logs/pipeline_state.json + 三闸输出", out="out/14-ops.md") + """
【你的唯一职责】守住 pipeline.py 与 submission_gate.py 本身，让它们在新赛题上仍然判得对。

【四项必做】
1) **向后兼容**：老 pipeline_state.json 里没有 G10–G15 键时必须显示 ??，不能崩。
2) **软闸门名单**：SOFT_GATES = {G10, G11, G14}。进这个集合的只有两类——(a) 依赖外部服务的门（视觉模型、网络），(b) 结构上可能不适用的门（无 TABLE_*、没上传模板）。新增闸门先问自己属不属于这两类。
3) **判据不许加 --quiet**：paper_data_check.py --quiet 只回报告路径，正文全无 → 解析必失败并误判成 None。
4) **三闸口径**：gauntlet 打 `N/M PASS` 且 exit 0；verify_numbers 打 `claims=N ... failures=0`；venue 打「N 项要你处理」。

【产出】out/14-ops.md：列「哪道门判不出 / 为什么 / 是不是软闸门 / 若换题会不会误判」。
【红线】不许为了让门变绿去改判据。判据宽了，下一轮就会把真问题放过去。"""))

# ---------------------------------------------------------------- 评审队 13 人

REVIEW_BRIEFS: list[tuple[str, str]] = []

REVIEW_BRIEFS.append(("合规审查员", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】RULES.md 的 C1–C12 条 + 官方格式规范 16 份；WORKFLOW.md §6、§5.1
【INPUT】main.tex / main.pdf / main.log / 官方规范原文
【OUTPUT】只写 review/01-compliance.md（UTF-8 无 BOM，末行 VERDICT: PASS|FAIL）
【纪律】每条结论引官方原文（文件 + 行号或 URL + 访问日期）；不许凭印象判合规

【本次任务】逐条过 C1–C12，每条给「条款原文 / 本稿状态 / 证据 / 判定」。先跑一条命令拿机器基线：
`E:\\Mini\\envs\\mathmodel\\python.exe ...\\scripts\\gauntlet_check.py <论文目录>`（16 项），再跑 `...\\scripts\\submission_gate.py <论文目录> --only venue --main main`。

【六条实测经验】
① 前置页顺序 control→summary→contents，页眉只有队号+页码。
② 正文 ≤30 页是硬判（R-V01 body=N）；超了只许把归档表搬附录，不许缩字号。
③ 全英文零汉字包含**附录源码**（venue 逐页扫 CJK，\\lstinputlisting 印出的中文注释同样命中）。
④ 队号非占位：\\baominghao{apmcm2699001}。
⑤ 参考文献要有类型标记且 ≥70% 被引（R-W04）。
⑥ 两遍 xelatex 均 exit 0 且无 Overfull \\hbox。

【红线】不许把「提醒」写成「不合规」。venue 的页数、AI 使用声明、参考文献核验三项是提醒，不拦。"""))

REVIEW_BRIEFS.append(("论文结构审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】templates/PAPER-TEMPLATE.md（族骨架）+ RULES.md 的结构条 + WORKFLOW.md §5
【INPUT】main.tex + out/00-problem.md（题面契约）
【OUTPUT】只写 review/02-structure.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给行号；只判结构不判措辞

【本次任务】四件事：
1) 族属判定（竞赛论文 vs 期刊 vs 学位）与必备章是否齐；
2) **每问闭环**：Q1..Qn 每问都要有「建模 → 求解 → 结果 → 一句结论」，缺哪个环节点名；
3) 页数预算：正文 ≤30 页，符号表/参数表/账本表应在附录；2026_C 把 14 行符号表从正文第 4 页搬到附录 A 才腾出空间；
4) 章节数与小节数是否失衡（基准带：sections 14 / subsections 43，一等奖 16 篇的 pct 分别 50.0 / 87.5）。

【红线】不许以「结构完整」一句带过。要给出「第 X 章第 Y 节缺 Z」。"""))

REVIEW_BRIEFS.append(("摘要与表达审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §5 摘要四段式 + writing.md
【INPUT】main.pdf 的摘要页
【OUTPUT】只写 review/03-abstract.md（末行 VERDICT: PASS|FAIL）
【纪律】用机器判据说话，不靠感觉

【本次任务】跑 `mmkit.review_bench.abstract_stats(pdf)`，报 words / numbers / density / verdict_words / verdict_numbers / question_refs。**判据是 verdict_words == "inside"，区间 327–449 词**。

【五条实测经验】
① 密度过高（>10）通常是塞了太多题给输入数——2026_C 首版 78 个数字 / 密度 17.49，删掉 20 个题给常数后降到 39 / 8.72。
② 每个数要配基准：「793 个工位」写成「八个等价最优里最小的那个」。
③ 关键词与第二段模型名同序。
④ 末段必须有一条**具体**局限，不许写「受数据限制」。
⑤ 摘要不许承诺正文没兑现的（「36 项检查全过」被 verify_numbers 推翻＝自证失败）。

【红线】只报「词数超了」不算审读。要给到「删哪一句、删完剩多少词」。"""))

REVIEW_BRIEFS.append(("题目契合度审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】problem.txt 全文 + out/00-problem.md
【INPUT】problem.txt + main.tex
【OUTPUT】只写 review/04-fit.md（末行 VERDICT: PASS|FAIL）
【纪律】逐条对照，每条给 problem.txt 行号 + main.tex 行号

【本次任务】把题面每条要求做成一张「要求 → 正文哪里兑现 → 是否兑现」的三列表。三件事：
1) 题面里每个「要你」的句子都必须有正文对应段；
2) **题面没要求但正文做了的**，要标出来（加分项还是跑题）；
3) 题给常数与正文数字逐个对，正文里出现题面没有的数必须标「自设」。

【红线】2026_C 踩过的坑：把七个功能面积写成「题给」，实际是自设，全文返修。这类必须点名。"""))

REVIEW_BRIEFS.append(("模型与检验审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §2、§11 第 1–4 条；RULES.md 的模型条
【INPUT】out/01-model.md、out/02-solve.md、data/results_*.json
【OUTPUT】只写 review/05-model.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给 JSON 键路径 + 复算命令

【本次任务】五类检查：
1) **口径**：松弛值有没有被当可达值写；阈值有没有标路径；分母说清没有；
2) **稳定性**：±10% 扰动是否真跑（不是解析推算）；不可行的那几次有没有单列；
3) **边界**：解在网格边界有没有标星 + 给放宽后的值；
4) **敏感性**：是否只报有利的一半（2026_C 的 Q3 面积 −5% 直接不可行，这一半必须写）；
5) **结论强度**：用「证明」的地方是不是只在一个读法下成立。

【红线】不许接受「模型合理」这种判语。要么给出反例，要么给出「在 X 读法下成立、在 Y 读法下不成立」。"""))

REVIEW_BRIEFS.append(("数据与代码审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §3、§5.1（G4/G5/G10/G12/G15）
【INPUT】code/*.py、data/*.json、data/ledger.json
【OUTPUT】只写 review/06-code.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给文件名 + 行号；能跑的必须真跑

【本次任务】四件事：
1) **台账**：每个外部数字有没有 url + 抓取时间 + sha256；竞赛题若全用附件数据，要看到 NOT-APPLICABLE + 附件清单；
2) **可重跑**：code/*.py 能不能一键重跑（2026_C 全链 252 ms），有没有硬编码的绝对路径；
3) **verify 覆盖率**：claims=N / checked=N / failures=0，DERIVED 里登记了多少派生值（2026_C 46 条）；
4) **产物新鲜度**：data/*.json 比 code/*.py 旧就是过期（R-V09），要重跑不是改时间戳。

【红线】不许把「有脚本」当成「可复现」。要给出重跑命令与实际输出。"""))

REVIEW_BRIEFS.append(("图表审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §4、§11 第 5–9 条
【INPUT】figures/*.pdf、figures/*.png、main.pdf
【OUTPUT】只写 review/07-figures.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给图号 + 页码 + 实测数值

【本次任务】六范式与误用 + 四项版式硬指标：
1) **图内出栏**：pymupdf 逐 span 比 MediaBox（416.5 pt），x1 > W-2.0 或 x0 < 2.0 即被裁；
2) **图内字号**：size < 6.0 and len(text) >= 3 即违规（6.0 会被记成 5.98，要求 ≥6.2）；
3) **图注只写图上真有的**：写「hatched cells」而图上没有 hatch 是硬伤；
4) **同轴混量纲**：比值 / 万元 / 百分比共轴必有一类变成细线；
5) 六范式误用（面积代替量值、雷达图「面积即总分」、Laffer/Pareto 不标拐点、敏感性只画有利的一半）；
6) 图数与小节数是否失衡（基准：figures 15 / subsections 43）。

【红线】不许只说「图太少」。要说「哪个结论缺图、该画什么图型」。"""))

REVIEW_BRIEFS.append(("创新性评估", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】RULES.md 的创新条 + out/07-innovation.md（若已存在）
【INPUT】out/01-model.md、out/02-solve.md、main.tex
【OUTPUT】只写 review/08-innovation.md（末行 VERDICT: PASS|FAIL）
【纪律】每个判断给行号；不许给「有一定创新」这种判语

【本次任务】按四类判：换表征 / 换约束表达 / 换规模（可扩展性主张）/ 跨学科映射。每条要写成**一句可检验命题 + 支撑数字 + 与常规做法的差别**。没有就明说「只有组合无机制」并指出缺哪一块。

【2026_C 的正面例子】「11 对不是搜出来的，是计数下界 ⌈6797.14/2000⌉+7=11 逼出来的」——把优化问题变成计数论证，可检验、可复算、和「用了 MILP」完全不同档次。

【红线】不许把「用了某算法/某库」当创新。评审要看的是：换个人用常规做法，能不能得到同一个结论。"""))

REVIEW_BRIEFS.append(("改进方案总编", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】review/ 下全部 12 份报告 + WORKFLOW.md §5.1
【INPUT】review/01..13 全部报告
【OUTPUT】只写 review/00-plan.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给「改哪个文件哪一行 / 改成什么 / 谁去改 / 估时」；不许合并成「整体提升」

【本次任务】把 12 份报告收敛成一张可执行的改稿清单，四级排序：
· **F 级（废稿级）**：不改就不能交——自证失败、合规硬项、提交件缺失；
· **J 级（判断级）**：改不改影响评奖档位——口径冲突、结论强于证据、数字错配；
· **K 级（口径级）**：同一个词被两种算法用过；
· **Z 级（增强级）**：加了更好——Robustness 小节、政策建议、Future Work。

【2026_C 的实测基线】42 项 = F 8 / J 16 / K 10 / Z 8，估 10h20m；改完 8 项 F + 16 项 J 从「二等奖下限偏上」进到一等奖带。

【红线】清单里每条都要能被人直接执行。写「加强稳定性分析」是废条；写「在 main.tex:919 后加一段，用 data/results_q5.json 的 rate_sensitivity 五个 delta 值」才是可执行。"""))

REVIEW_BRIEFS.append(("数字对账员", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §3（G5/G12）
【INPUT】main.tex + data/*.json + code/verify_numbers.py
【OUTPUT】只写 review/09-numbers.md（末行 VERDICT: PASS|FAIL）
【纪律】抽 10 个数，每个都要给出「正文行号 / 印的值 / JSON 键路径 / JSON 值 / 是否一致」

【本次任务】三件事：
1) 跑 `code/verify_numbers.py`，看 claims / checked / failures；
2) **抽 10 个数回 JSON 复算**（不要只信 verify 的输出，它可能压根没登记这个数）；
3) **单列「结构性空转」**：印了但没人用的数、只在附录出现一次的数、由产物自身决定的数（脚本字节数、页数）。

【四条实测经验】
① 匹配必须用词边界 (?<![\\d.])needle(?!\\d)，否则 "16" 会匹配到 "2016"。
② 派生值必须在 DERIVED 里登记算式（2026_C 46 条），否则变孤儿 token。
③ 附录 B 的计时句是自指的：改一次代码就变，判据要从「决定它自己的那一轮」排除。
④ 自指数字（「36 项检查」「1,704 个 token」）是最高危的一类——它随产物变化，写死必错。

【红线】不许只报「failures=0」。要报「有 N 个数根本没被 verify 覆盖」。"""))

REVIEW_BRIEFS.append(("口径冲突审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §11 第 1–4 条
【INPUT】main.tex 全文 + data/*.json 全部键
【OUTPUT】只写 review/10-caliber.md（末行 VERDICT: PASS|FAIL）
【纪律】每个冲突给两处行号 + 两个 JSON 键路径 + 建议改法

【你的唯一职责】与 数字对账员 分工：对账员查「这个数对不对」，你查「同一个词被两种算法用过」。这是 2026_C 返工量最大的一类（42 项里 10 项）。

【六个必查模式】
1) 松弛上界 vs 整数可达（0.86% vs 0.73%）；
2) 阈值沿哪条路径（4.608%/yr 是 W=800，W=793 是 4.506%）；
3) 分母不同（ROI 三比 0.1884/0.6716/1.6597，散差 8.81×）；
4) 合计口径（tiers 3+4+5 = 0.1317，tiers 4+5 只有 0.0148）；
5) 分母是 42 还是 30（12 次扰动不可行）；
6) 单位混用（m² gross / m² usable / 万元 / 10k CNY）。

【红线】只改措辞与限定语，不许改数字。改数字要退回 求解与优化手 重跑。"""))

REVIEW_BRIEFS.append(("版式与出栏审读", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】WORKFLOW.md §11 第 5–9 条
【INPUT】main.pdf、main.log、figures/*.pdf
【OUTPUT】只写 review/11-layout.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给页码 + 实测 pt 值 + 修法

【你的唯一职责】找「编译不报错、图看着正常、放大才发现断头句」的问题。四类：
1) 图内出栏（MediaBox 416.5 pt，x1 > W-2.0 或 x0 < 2.0）；
2) 图内字号（size < 6.0 and len >= 3；6.0 被记成 5.98）；
3) 表格 Overfull \\hbox（main.log 里 >1.0 pt 记一条、>10.0 pt 升级）；
4) 列表标签伸出左版心（enumitem 需 [leftmargin=*, align=left]）。

【实测过的三个坑】
· hatch="///" 生成 tiling pattern，PDF 里 BBox 远超画布 → 出栏检查误报，改虚线描边；
· sharey + 子图 set_yticks([]) 会连主图刻度一起清掉（21 个参数名全消失且不报错）；
· \\DeclareMathSizes 的键是 \\f@size 的精确十进制（10.53937 / 9.03374 / 7.52812 / 6.52437），写 {7.5} 匹配不上。

【红线】不许建议「缩字号」解决宽度问题。先改措辞，再放宽边距，最后才动字号且不低于 6.2 pt。"""))

REVIEW_BRIEFS.append(("修复排序手", """【工作区】E:\\数学建模\\APMCM2026_C　【解释器】E:\\Mini\\envs\\mathmodel\\python.exe
【必读】review/00-plan.md（若已存在）+ 其余全部报告
【INPUT】review/*.md 全部
【OUTPUT】只写 review/12-order.md（末行 VERDICT: PASS|FAIL）
【纪律】每条给「改动文件:行号 / 一句话改法 / 估时 / 依赖谁」

【你的唯一职责】把总编的清单排成「今晚必做 / 明天能做 / 可以不做」三档，并算总工时。排序依据：
1) **依赖优先**：改数字要先重跑 solve.py（252 ms），改图要重跑 make_figures.py（全量约 40 s）再 gen_index.py；
2) **一次编译能带走的**：所有改 main.tex 的项攒成一批，只编译一次；
3) **连锁项**：改任何 code/*.py 都会让 tab:code 的字节数过期 → 必须跟着跑 gen_index.py；
4) **不可逆项优先**：删内容比加内容风险高，先做加法。

【实测基线】2026_C 一轮 42 项、10h20m；F 级 8 项约 1h，J 级 16 项约 6h，K 级 10 项约 2h，Z 级 8 项约 1.5h。

【红线】不许给「并行做」这种建议——本机是单会话串行，且改同一批文件会互相覆盖。"""))


def write_briefs(root: pathlib.Path, squad: str, slug: str, items: list[tuple[str, str]]) -> list[dict]:
    d = root / slug
    d.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, (name, body) in enumerate(items, 1):
        fn = f"{i:02d}-{name}.md"
        p = d / fn
        p.write_text(body.strip() + "\n", encoding="utf-8", newline="\n")
        manifest.append({"squad": squad, "name": name, "file": f"{slug}/{fn}", "chars": len(body.strip())})
    return manifest


def main() -> None:
    m = []
    m += write_briefs(HERE, MAIN, "main", MAIN_BRIEFS)
    m += write_briefs(HERE, REVIEW, "review", REVIEW_BRIEFS)
    (HERE / "MANIFEST.json").write_text(
        json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    print(f"main={len(MAIN_BRIEFS)} review={len(REVIEW_BRIEFS)} total={len(m)}")
    for e in m:
        print(f"  {e['chars']:>5d}  {e['squad']} / {e['name']}  -> {e['file']}")


if __name__ == "__main__":
    main()
