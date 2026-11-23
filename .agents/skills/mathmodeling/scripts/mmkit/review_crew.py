"""评审队的名册、依赖链与任务正文（与建稿队分开，但共用 crew.py 的派单/落地/超时判据）。

为什么评审要单独一队而不是复用建稿队那 18 人：
建稿队的 brief 是"产出一份东西"，评审队的 brief 是"对一份东西下判断并要求给改法"。
两者对同一个"输出文件"的写法要求不同（评审要写 finding 表 + 一句可执行改法），
混在一起会让成员按老 brief 交"看起来像产出"的空壳。

13 个成员的依据全部是可核文件，不许引用"常识"：
  C1..C12  → APMCM-PROBLEMS\\_official_criteria.json（每条带 file:line 或扫描件页号转录）
  题目侧    → APMCM-PROBLEMS\\_official_evidence.json（35 份真题，8 个关注点，233 条引文已逐条回原文）
  一等奖侧  → APMCM-PROBLEMS\\_award_pdfs.json / _award_outline.json / _award_text\\
  摘要基准  → mmkit.review_bench.ABSTRACT_BENCH（16 篇英文一等奖实测）
"""
from __future__ import annotations

from pathlib import Path

from . import pyexe as _pyexe
from . import corpus as _corpus

TEAM_NAME = "数学建模评审小队"

# 队伍简介（UI 卡片上显示；空着会像"这支队伍啥也没有"）。依据是可核的原件，不是经验：
#   E:\数学建模\APMCM-PROBLEMS\  2015–2026 共 35 份真题 / 16 份官方格式规范 / 22 份一等奖 PDF，逐份带 sha256
TEAM_DESCRIPTION = (
    "写完论文之后的挑剔小队，只对已经存在的稿子下判断并给可执行改法。十三角色：合规（C1–C12 官方条款）→ "
    "结构（族属/必备章/每问闭环/页数预算）→ 摘要表达（四段式+数字配额）→ 题目契合（题面每条要求逐条兑现）→ "
    "模型与检验（口径/稳定性/边界/敏感性/结论强度）→ 数据代码（台账/可重跑/verify 覆盖率/产物新鲜度）→ "
    "数字对账（抽 10 个数回 JSON 复算，单列结构性空转）→ 口径冲突（同一个词被两种算法用过）→ "
    "图表（六范式与误用）→ 版式与出栏（图自己的 MediaBox 贴边、hatch 图元、Overfull）→ "
    "创新性（四类创新+可检验命题）→ 总编（四级排序、今晚必做）→ 修复排序手（今晚必做/明天能做/可以不做 + 工时）。"
    "依据全部是可核原件：35 份真题、16 份官方格式规范、22 份一等奖 PDF。"
    "派单前先由脚本生成 review/00-metrics.md 当唯一口径基线；报告只准对着它说话。"
)

# ---------------------------------------------------------------- 成员名册
MEMBERS = [
    # (name, permission)
    ("合规审查员", "read-only"),        # 12 条官方硬项
    ("论文结构审读", "read-only"),      # 骨架族 / 章节完整性 / 页数预算
    ("摘要与表达审读", "read-only"),    # 摘要四段式 + 数字配额 + 英文可读性
    ("题目契合度审读", "read-only"),    # 是否回答了官方题面真正问的事
    ("模型与检验审读", "read-only"),    # 假设/口径/稳定性/敏感性是否站得住
    ("数据与代码审读", "read-only"),    # 溯源台账 / 代码可复跑
    ("数字对账员", "read-only"),        # 抽 10 个印出来的数，逐个回 JSON/PDF 复算
    ("图表审读", "read-only"),          # 六范式与误用
    ("创新性评估", "read-only"),        # 四类创新 + 可检验命题
    ("口径冲突审读", "read-only"),      # 同一个词被两种算法用过（2026_C 42 项里占 10 项）
    ("版式与出栏审读", "read-only"),    # 读者看不到的断头句：MediaBox 贴边 / hatch 图元 / Overfull
    ("改进方案总编", "workspace-write"),  # 汇总成一份可执行的修改清单
    ("修复排序手", "workspace-write"),    # 写 review/12-order.md —— 必须是可写，read-only 落不了盘
]

# 依赖：几乎都只依赖"论文本身 + 官方语料"，所以第一波可以并发。
# 只有总编与排序手要等前面全部落地。
DEPENDS = {
    "合规审查员": [],
    "论文结构审读": [],
    "摘要与表达审读": [],
    "题目契合度审读": [],
    "模型与检验审读": [],
    "数据与代码审读": [],
    "数字对账员": [],
    "图表审读": [],
    "创新性评估": [],
    "口径冲突审读": [],
    "版式与出栏审读": [],
    "改进方案总编": ["review/01-compliance.md", "review/02-structure.md", "review/03-abstract.md",
                     "review/04-fit.md", "review/05-model.md", "review/06-code.md",
                     "review/07-figures.md", "review/08-innovation.md", "review/09-numbers.md",
                     "review/10-caliber.md", "review/11-layout.md"],
    "修复排序手": ["review/00-plan.md", "review/01-compliance.md", "review/02-structure.md",
                   "review/03-abstract.md", "review/04-fit.md", "review/05-model.md",
                   "review/06-code.md", "review/07-figures.md", "review/08-innovation.md",
                   "review/09-numbers.md", "review/10-caliber.md", "review/11-layout.md"],
}

OUTPUT_OF = {
    "合规审查员": "review/01-compliance.md",
    "论文结构审读": "review/02-structure.md",
    "摘要与表达审读": "review/03-abstract.md",
    "题目契合度审读": "review/04-fit.md",
    "模型与检验审读": "review/05-model.md",
    "数据与代码审读": "review/06-code.md",
    "数字对账员": "review/09-numbers.md",
    "图表审读": "review/07-figures.md",
    "创新性评估": "review/08-innovation.md",
    "口径冲突审读": "review/10-caliber.md",
    "版式与出栏审读": "review/11-layout.md",
    "改进方案总编": "review/00-plan.md",
    "修复排序手": "review/12-order.md",
}

# 三波：11 个审读员并发 → 总编收口 → 排序手把清单排工期。
WAVES = [
    ["合规审查员", "论文结构审读", "摘要与表达审读", "题目契合度审读",
     "模型与检验审读", "数据与代码审读", "数字对账员", "图表审读", "创新性评估",
     "口径冲突审读", "版式与出栏审读"],
    ["改进方案总编"],
    ["修复排序手"],
]

HOUSE = "\n".join([
    "【工作区】{ws}",
    "【被测论文】{paper}",
    "【解释器】{py}（带 numpy/pandas/matplotlib/torch；若路径不存在，设 MM_PY）",
    "【官方依据】{corpus}：problems/<年份>/（2019–2025 历年真题与附件）、"
    "awards/<年份>/（2019–2025 一等奖 PDF）、rules/（官方格式规范与承诺书）、"
    "_PROVENANCE.md（每份文件的 sha256 与核验判据）。"
    "引用真题必须写文件名 + 行号；引用获奖稿必须写文件名 + 页码。",
    "【禁止】不许凭印象说\"一等奖都这样\"——要说\"C5 在 7 份官方规范里命中 9 处\"这种可核形式；"
    "没有出处的判断标注 [判断] 并说明你的理由链。",
    "【OUTPUT】只写下面【你的输出】给出的那一个文件；UTF-8 无 BOM；首行 BYTES <n>；"
    "结论表格必须能被别人拿同一份 PDF 复算（写清命令）。末行 VERDICT: PASS|FAIL。",
    "【先跑机器口径再读文】动手看正文之前，先跑这三条，把输出贴进报告开头（它们能替你抓掉"
    "一半的\"我以为\"）：①`review_check.py <论文目录>`（12 条官方硬项）；"
    "②`gauntlet_check.py <论文目录>`（R 系列 16 项，含基准带与页面编号连续性）；"
    "③`python -m mmkit.figfont <main.pdf>`（图内有效字号）。"
    "三条都过还剩下的问题才是要你读出来的问题。",
    "【先确认被测件与数据层同代】比较 main.pdf 与 data/*.json、tables/*.tex、figures/*.pdf 的 mtime；"
    "若数据层更新，就在报告开头写\"被测件落后 N 小时，以下数字可能已被重跑覆盖\"，"
    "并以你现场跑出来的数为准（R-V11：报告是快照）。",
    "【四类高频可复算缺陷，先逐类查一遍】①口径混用（权重 vs 有效贡献、逐帧 pool vs 每人 p95、"
    "抽取耗时 vs 端到端）；②倍数与百分数（同一现象两个分母）；③多重比较（同一张表 k 个检验，"
    "必须给 BH/Bonferroni 后的 q）；④图表刻度（有效字号 < 6 pt 用 figfont 量，不靠看图）。"
    "这四类在 APMCM2025_C 与 2018A 两次评审里每次都命中，比\"创新性不足\"更值得写。",
    "【先读 00-metrics.md，那是别人已经跑过的】`{paper}\\review\\00-metrics.md` 由派单脚本在派你之前"
    "自动生成（四条机器判据的原始输出 + main.pdf/main.tex/data 的 mtime 与 sha256）。它是口径的**唯一基线**："
    "你自己的结论若与它不一致，必须在报告里并列两个数并说明\"我在什么时刻、对哪个文件重跑\"，"
    "不许只写你自己的那个（2018A 就出过一次：报告评的是 68 页的旧 PDF，定稿已经 72 页）。",
    "【印出来的数必须能被别人复算】你对正文里任何一个数字下判断之前，先找它的产物键"
    "（`data/*.json` 里的键名）或 `code/verify_numbers.py` 的 claim 名字。找不到产物键的数字是**缺陷本身**，"
    "不是\"需要更精确\"——2018A 的摘要印过 \"749 feature values\"，而 25×74=1850，且 749 在任何 JSON 里都不存在。",
    "【不适用】本题不涉及你的职责时写 NOT-APPLICABLE: <理由>。",
])

RC = str(Path(__file__).resolve().parent.parent / "review_check.py")
PY = _pyexe.py()

TASKS = {
    "合规审查员": (
        "只做\"不合规就废稿\"的 12 条官方硬项。先跑\n"
        f"  {PY} {RC} <被测PDF> --json review/01-compliance.json\n"
        "再逐条回 _official_criteria.json 取原文出处。"
        "输出表：判据编号 | 官方原文（引号内逐字）| 出处 file:line | 论文实测值 | 结论 PASS/FAIL | 若不改会怎样。"
        "特别核对：C4 第一页摘要页与第二页目录、C5 页眉（**目录页也要有队号与页码**，只写 CONTENTS 就是 FAIL）、"
        "C7 零中文（**只判正文，附录汉字单列**）、C9 附录软件名与**全部**源码"
        "（对照 `code/*.py` 实数与 `\\lstinputlisting` 数，并检查附录 B 复现命令点名的脚本是否都在 listing 里）、"
        "C11 队号（**两层**：字形占位 XXXXX，以及正文自称\"not a valid team number / placeholder\"的语义占位）、"
        "C3 交付件名是否 \"题号+队号\"（main.pdf 不合规，要 A<队号>.pdf）。"
        "任何一条 FAIL 就是废稿级，必须写在最前面。"),
    "论文结构审读": (
        "对照 22 篇一等奖的实测骨架（_award_outline.json 里的章节序列），回答三件事："
        "1) 本文属于哪一族（A/B/C/D/E），该族的必备章有哪些，本文缺哪章（给一等奖里的反例与正例）；"
        "2) 每问是否形成\"预处理→模型→求解与结果→检验\"的闭环，缺哪一环；"
        "3) 页数预算：正文页数 vs 一等奖 p25/p75（mmkit.review_bench.award_bench()），"
        "超了只能把归档表搬附录，列出可以搬的具体表。"),
    "摘要与表达审读": (
        "摘要按 16 篇英文一等奖的实测基准判（median 363.5 词、p25 327、p75 449、"
        "数字 median 11.5、最少 2、零数字 0/16）：先跑\n"
        f"  {PY} -c \"import sys;sys.path.insert(0,r'<skill>\\scripts');"
        "from mmkit import review_bench as R;print(R.abstract_stats(r'<被测PDF>'))\"\n"
        "再逐段判四槽位（Background and Task / Modeling Framework / Results per Question / "
        "Validation and Limitation）；指出哪一段是\"纯方法清单\"或\"纯数据堆砌\"（一字奖里的 P1-a/P1-b 反例）。"
        "然后给一段可直接替换的英文改写（保留作者的模型名，不许换说法）。"),
    "题目契合度审读": (
        "从 APMCM-PROBLEMS\\PROBLEMS\\ 取当年该题原题全文，逐句列出题面的\"要求你\"句式，"
        "再在论文里找对应的交付物。输出表：题面要求（原句+行号）| 论文兑现位置（章/表/图）| "
        "兑现程度（数值/定性/没做）。"
        "重点查 _official_evidence.json 里频次高的几类（给数据 19/35、政策建议 19/35、"
        "预测时序 13/35、要求具体数值 13/35），本文漏了哪一类。"
        "**两条容易整条漏掉的**：①题面里的\"描述性约束\"（如 2018A 的 \"There are three full gaits\"）"
        "不算祈使句，但论文若给了相反的断言（\"often fewer than two\"）就是可复算的错误，要用数据判谁对；"
        "②题面明确要\"给建议/给方案\"的小问，必须有可执行交付物（人群、剂量、判定阈值），"
        "只写一句队列级结论＝没做。"),
    "模型与检验审读": (
        "只找能推翻结论的地方：1) 口径（谁和谁比、分母是谁、基期是哪年）；2) 稳定性必须报不利的一半"
        "（排序没动但 top-1 只活 x% 的情况必须写出来）；3) 边界解（最优点落在搜索网格边上要标星并给放宽后的值）；"
        "4) 敏感性强度（扰动 ±10% / 重抽样 / Sobol 三档至少两档）；5) 结论是否强于证据（逐句找出）。"
        "每条给出文件行号与可复算命令，并给\"最小改法\"。"),
    "数据与代码审读": (
        "核三件事：1) 台账 data/ledger.json 每条是否有 url/source + sha256 + fetched_at；"
        "2) 抓取与建模脚本能否重跑（真跑一次，报 exit code 与耗时）；"
        "3) `code/verify_numbers.py` 是否真能对上 main.tex 的每个关键数字"
        "（词边界匹配；**并且要看它的 coverage 行**：`N printed numbers bound, M tokens not bound`，"
        "M 里凡有结果的数字就是漏绑；还要看有没有 `needle=None` 这类结构性空转、永远不可能失败的 claim）。"
        "输出\"可复现性等级\"：全可复算 / 部分 / 不可复算，并给出理由。"
        "**另外必查**：产物是否比脚本旧（`mmkit.freshness`）；附录列出的脚本与 `code/*.py` 是否一致；"
        "同一份 data 是否被两处不同口径引用（例如同一量在两节里一个用 21.1% 一个用 15%）。"),
    "图表审读": (
        "按六范式（情景对比分组柱 / 敏感性龙卷风与秩漂移 / Laffer 与 Pareto / 雷达 / 热力图 / 流程图）"
        "逐图判：图是否自解释（单位、样本量、误差带、口径在 caption 里）、是否用面积代替量值、"
        "Pareto/Laffer 是否标了拐点、敏感性是否只画了有利的一半。"
        "输出表：图号 | 范式 | 误用类型 | 改法（改 caption 还是重画）。"),
    "创新性评估": (
        "四类创新（换表征 / 换约束表达 / 换规模 / 跨学科映射）逐个套，"
        "给出\"只有组合无机制\"还是\"有可检验命题\"。"
        "必须写成一句可检验命题 + 支撑数字 + 与常规做法的差别。"
        "若确实没有，就明确写\"当前无创新机制\"，并给两条最省时的施工路径（各写清改哪个文件、"
        "预期得到什么数字）。不许把\"用了很多方法\"当成创新。"),
    "数字对账员": (
        "你的唯一工作：**证明正文里的数字站得住，或者证明它站不住**。步骤固定，不许自由发挥：\n"
        "1) 跑 `{paper}\\code\\verify_numbers.py`，把最后三行（claims/failures/coverage）原样贴上来；\n"
        "2) 从 PDF 正文里**抽 10 个**数字（覆盖摘要 3 个、每问 1–2 个、表 2 个；避开年份与题号），"
        "逐个写：印的值 | 产物文件与键名 | 现场复算的值 | 差 | 结论；\n"
        "3) 对每个抽样数字判**三件事**：能不能从 `data/*.json` 找到键、键算出来是否等于印的数、"
        "该键是否由**当前版本**的脚本生成（比 mtime）；\n"
        "4) 单独列\"结构性空转\"：`verify_numbers.py` 里有没有 needle 为空、或断言恒真的条目；"
        "以及正文里有多少数字**没有任何 claim 覆盖**（跑它的 coverage 行，把 M 列表里属于结果的挑出来）；\n"
        "5) 结论只能三选一：`每个抽样数都可复算` / `存在 N 个不可复算`（列出）/ `无法判断`（说明缺什么）。\n"
        "禁止：用\"看起来合理\"\"与常识一致\"代替复算；禁止只贴 verify_numbers 的 PASS 而不抽样。"),
    "口径冲突审读": (
        "只找一件事：**同一个词被两种算法用过**。这类缺陷比算错数更隐蔽——两个数各自都对，"
        "但读者以为自己在看同一个量。2026_C 的 42 项审阅清单里有 10 项属于这一类。\n"
        "做法：\n"
        "1) 把 main.tex 里出现的量化名词抽出来（占比/额度/利用率/NPV/回报率/闲置面积/敏感度…），"
        "每个词找出它在正文里出现过的**所有**取值；\n"
        "2) 对每个取值回溯到 `data/*.json` 的键，列出**每个键由哪段代码算出**（`code/*.py` 的函数名与行号）；\n"
        "3) 两个取值来自不同函数、或同一函数不同参数，就是口径冲突，必须并列两个数并指出哪个分母是哪段代码用的；\n"
        "4) 给处置建议三选一：只保留一个口径并改掉另一处 / 两个都留但改名区分（如 `净回报` vs `毛回报`）/ "
        "在表注里写明各自定义。\n"
        "**已知的典型**：`4.608%` 与 `4.506%`（W=800 与 W=793 两个阈值）、`0.86%` 与 `0.8608`（相对量 vs 效益值）、"
        "`0.1317` 是 tiers 3+4+5 而 `0.0148` 是 tiers 4+5、`532` 与 `300`（运行费含不含折旧与维护）。\n"
        "输出表：词 | 取值 A（出处 file:line + JSON 键 + 生成函数）| 取值 B（同）| 是否冲突 | 处置建议。"
        "禁止把\"两个数差不多\"当结论——要么给出各自口径，要么给出哪个是错的。"),
    "版式与出栏审读": (
        "只查**读者看不见的东西**：被 PDF 裁掉的文字、冲出栏的图表、跑出页面的表格。\n"
        "三条判据，全部可机器复算：\n"
        "1) **图自己的 MediaBox**：逐张 `figures/*.pdf` 用 pymupdf 取每个 span 的 bbox 与该页 `page.rect` 比，"
        "`x1 > W-2.0 or x0 < 2.0 or y1 > H-2.0 or y0 < 2.0`（`len(text) >= 3`）就是贴边；"
        "**注意不能用主文档版心判**——`main.tex` 里 `width=1.0\\linewidth` 使缩放比恒 1.0，图内超出的部分被直接裁掉，"
        "读者看到的是断头句（2026_C 第 12 页那句 `ity utilisation η (dimensionless, ...` 就是这么来的）。\n"
        "2) **`get_bboxlog()` 的图元**：matplotlib 的 `hatch` 生成 tiling pattern，BBox 远超画布，"
        "视觉被裁但出栏检查数得到；`fill-path`/`stroke-path` 的矩形也要与版心比。\n"
        "3) **Overfull \\hbox**：解析 `main.log` 的 `Overfull \\hbox \\(([0-9.]+)pt too wide\\)`，"
        "`>1.0pt` 记账、`>10pt` 必改；改法是把整张 tabular 包进 footnotesize 并缩 tabcolsep（见 main.tex 里 tab:map 的写法），或换 shortstack。\n"
        "另查：页眉页脚是否**每页**都有队号与 `Page n of N`（`\\pagestyle` 与 `\\setcounter{page}` 的组合最容易错）、"
        "图注是否写了图上不存在的视觉语法（hatch/marker/dark cell）、同轴多柱是否同量纲。\n"
        "输出表：页/图 | 现象（贴边 N pt / Overfull N pt / 图注与图不符）| 判据命令 | 改法。"),
    "修复排序手": (
        "读 `review/00-plan.md` 与其余全部报告，产出一份**按工期排的施工单**。\n"
        "总编已经分了四级（废稿级/结论级/口径级/增强级），你的增量是三件他没做的事：\n"
        "1) **算工时**：每一项给一个实测过的耗时（改文件 X 分钟 + 重编译 40 秒 + 重跑三闸 2 分钟 + "
        "图表全量重生成 N 分钟），并按\"改一处会连带触发什么\"列出连锁项——"
        "改 `code/make_figures.py` 必然连带 `code/gen_index.py`、`figures/code_index.tex`、`xelatex`×2、`verify_numbers`；\n"
        "2) **排三个桶**：`今晚必做`（废稿级 + 结论级，且不依赖别人）／`明天能做`（口径级、需要重跑数据）／"
        "`可以不做`（增强级，写清不做的代价）。每桶按\"做完之后哪道闸从 FAIL 变 PASS\"排序，"
        "因为闸门过不去就没法提交；\n"
        "3) **标出冲突项**：两份报告对同一处给了不同改法时，并列两种并写\"选 A 的代价 / 选 B 的代价\"，"
        "不替人裁决。\n"
        "输出格式固定：桶 | 序号 | 改什么（file:line）| 怎么改 | 改完怎么验（命令）| 预计分钟 | 卡在哪道闸 | 依赖谁。"
        "最后一行给总工时与\"今晚能做完的分钟数\"。禁止写\"加强分析\"这类不可执行的句子。"),
    "改进方案总编": (
        "读 review/01..09 九份报告（合规/结构/摘要/契合/模型/代码/数字/图表/创新），产出一份可执行清单："
        "按【废稿级 / 结论级 / 口径级 / 增强级】四级排序，"
        "每项写：改哪个文件哪一行、改成什么、改完怎么验（命令）、预计耗时、依赖谁。"
        "**两条纪律**：①报告的 mtime 早于 `00-metrics.md` 的，先看它说的那份 PDF 是不是当前这份"
        "（2018A 就出现过：4 条废稿级里有 3 条是对旧 PDF 说的，改完已不存在）；"
        "②同一件事在两份报告里口径不同（一个说 15%、一个说 21.1%）时并列两个口径并指出哪个分母是哪个人用的，"
        "不要替他们裁决。"
        "禁止写\"加强分析\"\"完善模型\"这类不可执行的句子。"
        "最后给一句话结论：这篇现在能拿什么档，改完这 N 项能到什么档，依据是哪几条判据/反例。"),
}


def _fill(text: str, ws: Path, paper: Path) -> str:
    """只替换 {ws}/{paper}/{py}/{corpus} 四个字面量，不走 str.format。

    为什么不 format：任务正文里全是 LaTeX 与 Python 代码，`\\setlength{\\tabcolsep}`、
    `{page}`、`{n}` 这类花括号会被当成占位符并抛 KeyError（实测 'page'）。
    """
    return (text.replace("{ws}", str(ws))
                .replace("{paper}", str(paper))
                .replace("{py}", PY)
                .replace("{corpus}", str(_corpus.corpus_root())))


def full_briefs(ws: Path, paper: Path) -> dict[str, str]:
    """生成 13 人完整 brief（供 crew.push_briefs 用）。

    输出路径一律挂在 **paper** 下，不挂 ws：2018A 第一轮把 `ws`（工作区根）当输出根，
    8 份报告全落在 `review/` 而不是论文目录里，`outcome()` 于是报 8/8 missing。
    协调器传什么根，审读员就写哪儿 —— 所以根要在这里定死，不靠调用方自觉。
    """
    out = {}
    for name, _perm in MEMBERS:
        deps = DEPENDS.get(name, [])
        dep_line = "、".join(str(paper / d) for d in deps) if deps else "（无上游依赖，可与同波其他成员并发）"
        head = _fill(HOUSE, ws, paper)
        body = _fill(TASKS[name], ws, paper)
        out[name] = (f"{head}\n【依赖产物】{dep_line}\n"
                     f"【你的输出】{paper / OUTPUT_OF[name]}\n\n【本次任务】\n{body}")
    return out
