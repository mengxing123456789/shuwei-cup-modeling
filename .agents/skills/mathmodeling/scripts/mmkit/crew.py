"""小队派单：把 18 个成员的 brief（评审模式 13 个）按队号派出去，并轮询到全部落地。

设计取舍：
- brief 正文在这里生成，而不是从 build_squad.mjs 读 —— 那份是"定义数据"，
  这里要的是"每次派单的任务正文"，两者寿命不同。共同的部分（HOUSE 纪律块、
  依赖链）以 DEPENDS 为唯一事实来源，改一处即可。
- 派单前必须先把成员 brief 打过一遍 `ensure_briefs()`：老成员的 brief 里没有
  INPUT/OUTPUT/BLOCKED 三段，测验证明那样会引用旧版产物。
- 轮询只认"输出文件存在且 > 0 字节"，不认会话状态。测验里有一份产物 36 步
  正常结束却没写文件，会话状态骗过人。
"""
from __future__ import annotations

import json
import shutil
import os
import subprocess
import sys
import time
from pathlib import Path

from . import pyexe as _pyexe

TEAM_ID = "61cec604-e7fa-4468-9a84-40757e4292c6"   # 建稿队（18 人）
REVIEW_TEAM_ID = "b68d6335-b534-4f4b-aec7-0b2d56b501b8"  # 数学建模评审小队（13 人）
TEAM_NAME = "数学建模小队"

# 队伍简介（UI 卡片显示）。brief 里的绝对路径是**上次派单**用的论文目录；
# 每次 crew.dispatch(ws, paper, …) 会按传入的 paper 重写全部 brief，所以换题不需要手改。
TEAM_DESCRIPTION = (
    "亚太杯/国赛/数维杯数学建模全流程小队（18 人，十波）。给一个题目，产出可提交的成稿："
    "题目侦察 → 真题对标（2019–2025 数维杯真题+获奖论文语料，查同型题与那批稿子的章法）→ "
    "建模架构 → 数据溯源（抓数必留 url+时间+sha256）→ 求解与优化 / 代理模型训练 → "
    "数值对账（正文每个数回到 JSON 键）→ 口径审计（同一个词不许被两种算法用过）→ "
    "图表（图内 ≥6 pt、六范式、不被 MediaBox 裁）→ 论文撰写 → 版式与出栏（出栏看的是图自己的画布）→ "
    "附录与自指（由产物决定的值不许手写）→ 格式合规（C1–C12）→ 对抗评审 / 创新挖掘 → "
    "时间与质检 → 流水线运维（守 pipeline.py 与二十道门本身）→ 调度。"
    "每份 brief 都带可复算命令、法定产物路径与一句红线；"
    "跑的是 scripts/pipeline.py 的 s1–s7 与 G1–G20，判据全部可机器复核，不靠「看起来对」。"
)
# 不写死路径：先找随技能内置的副本，再退回用户级 squad-runner。
_HERE = Path(__file__).resolve()
_CANDIDATES = [
    _HERE.parents[2] / "vendor" / "discover.mjs",
    Path.home() / ".agents" / "skills" / "squad-runner" / "lib" / "discover.mjs",
]
RUNNER = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])
NODE = next(
    (p for p in (Path(shutil.which("node") or ""), Path(r"C:\Program Files\nodejs\node.exe")) if str(p) and p.exists()),
    Path("node"),
)

# 手写 brief 的唯一来源：`squads/main/NN-<成员名>.md` 与 `squads/review/NN-<成员名>.md`。
# 为什么存在：brief 正文里全是"上次踩过的坑"这类只能人工审的东西，写进 py 常量后
# 每次 diff 都被行号噪声淹掉；搬到 md 里就能逐份 review、逐份改。
BRIEF_ROOT = Path(__file__).resolve().parents[2] / "squads"
BRIEF_SQUAD = "main"

DEPENDS = {
    "题目侦察手": [],
    "真题对标手": [],   # 只读题面（problem/problem.txt 是用户给的输入，不由任何成员产出）
    "建模架构手": ["out/00-problem.md", "out/15-benchmark.md"],
    "数据溯源手": [],
    "求解与优化手": ["out/01-model.md"],
    "代理模型训练手": ["out/01-model.md"],
    "数值对账手": ["data/ledger.json"],
    "口径审计手": ["out/02-solve.md", "out/03-numbers.md"],
    "图表手": ["out/03-numbers.md"],
    "论文撰写手": ["out/01-model.md", "out/03-numbers.md", "out/08-figures.md", "out/05-caliber.md"],
    "版式与出栏手": ["out/09-writing.md", "out/08-figures.md"],
    "附录与自指手": ["out/09-writing.md"],
    "格式合规手": ["out/09-writing.md", "out/10-layout.md", "out/13-appendix.md"],
    "对抗评审手": ["out/09-writing.md", "out/03-compliance.md"],
    "创新挖掘手": ["out/01-model.md", "out/03-numbers.md"],
    "时间与质检手": [],
    "调度手": [],
    "流水线运维手": [],
}
OUTPUT_OF = {
    "题目侦察手": "out/00-problem.md",
    "真题对标手": "out/15-benchmark.md",
    "建模架构手": "out/01-model.md",
    "数据溯源手": "data/ledger.json",
    "求解与优化手": "out/02-solve.md",
    "代理模型训练手": "out/12-training.md",
    "数值对账手": "out/03-numbers.md",
    "口径审计手": "out/05-caliber.md",
    "图表手": "out/08-figures.md",
    "论文撰写手": "out/09-writing.md",
    "版式与出栏手": "out/10-layout.md",
    "附录与自指手": "out/13-appendix.md",
    "格式合规手": "out/03-compliance.md",
    "对抗评审手": "out/04-review.md",
    "创新挖掘手": "out/07-innovation.md",
    "时间与质检手": "out/06-gate.md",
    "调度手": "out/11-dispatch.md",
    "流水线运维手": "out/14-ops.md",
}

# 波次：同一波内的成员互不依赖，可以并发派；波次之间必须等上一波全部落地。
# 真题对标手放在第 0 波：它只依赖 problem/problem.txt，与题目侦察手并排跑最省一个波次；
# 它的产物 out/15-benchmark.md 进 建模架构手 的 DEPENDS，于是「先对标再建模」由依赖保证，
# 不靠排期碰运气。
WAVES = [
    ["题目侦察手", "数据溯源手", "真题对标手"],
    ["建模架构手"],
    ["求解与优化手", "代理模型训练手", "数值对账手"],
    ["口径审计手"],
    ["图表手"],
    ["论文撰写手"],
    ["版式与出栏手", "附录与自指手"],
    ["格式合规手"],
    ["对抗评审手", "创新挖掘手"],
    ["时间与质检手", "调度手", "流水线运维手"],
]

# 权限：每份 brief 都要求写一个产物文件，所以全员 workspace-write。
# （2026-11-18 之前 题目侦察手 / 时间与质检手 是 read-only，结果是它们写不出
# out/00-problem.md 与 out/06-gate.md，G1/G9 永远拿不到 VERDICT。已一并提上来。）
# 空表 = 全员 workspace-write。
# 2026-11-18 改：原来 `题目侦察手` 与 `时间与质检手` 是 read-only，实测 read-only 的成员
# **写不出产物**，于是 G1（题面）与 G9（评审收口）永远拿不到 VERDICT，整条链在 s1 就卡死。
# 两个角色的纪律（只找问题、不改上游）靠 brief 里的【纪律】段约束，不靠文件系统权限——
# 权限只能证明"他没写"，不能证明"他查对了"。
PERMISSION = {}

HOUSE = "\n".join([
    "【工作区】{ws}",
    "【被测论文】{paper}",
    "【解释器】{py}（带 numpy/pandas/matplotlib/torch；裸 python 无第三方库。若路径不存在，设环境变量 MM_PY 指向本机装了这些库的 Python）",
    "【INPUT】先 Read 紧跟本段之后列出的依赖产物。任何一份不存在，只写一行 BLOCKED: <缺哪个文件> 到你的输出文件并停止，不许补做上游的活。",
    "【OUTPUT】你只能写一个文件：下面【你的输出】给出的那个绝对路径。不许改文件名、不许另起名（实测有成员写成 out/final-check.md，巡检判为未交付）。UTF-8 无 BOM；写完 Read 回来确认字节数 > 0，正文首行写 BYTES <n>。",
    "【不适用】本题不涉及你的职责时，写一行 NOT-APPLICABLE: <理由>，不要空转，也不要假装 PASS。",
    "【纪律】每条结论附可复算的命令或文件行号；改动被测文件前先备份；末行写 VERDICT: PASS|FAIL。",
])

TASKS = {
    "题目侦察手": (
        "读赛题 PDF（{problem_pdf}）与附件数据，产出 out/00-problem.md：\n"
        "1) 逐句抄出\"要求你\"的句子，标出处；2) 每个子问的交付物形态（数值/方案/排序/预测/机制）；"
        "3) 附件数据的行数、列名、缺失率；4) 三处最容易被误读的表述，各写\"读者会以为 X，实际是 Y\"；"
        "5) 题型判定（A 图像/几何、B 物理优化、C 数据统计、D 组合整数、E 聚类时序）并给出判据。"),
    "真题对标手": (
        "用本地语料（2019–2025 数维杯真题 + 一等奖论文）回答三件事，产出 out/15-benchmark.md：\n"
        "1) 近邻检索：corpus_index.py --query-file problem/problem.txt --top 8，再补两轮人工词；"
        "每条命中给「年份 题号 类型 标题 + 相似在哪一句」；\n"
        "2) 同型题解法谱系：--year Y --problem X --kind paper 列出那批论文，抽 2–3 篇读结构，"
        "写「子问题 / 用了什么模型 / 用了什么数据 / 有没有检验」四列表；\n"
        "3) 章法惯例与照搬陷阱：各给三条。语料数字必须标注「引自己获奖论文，不是本题结果」。"),
    "数据溯源手": (
        "为论文中每一个外部数字建立台账 data/ledger.json：每条 source/api/indicator/value/unit/period/"
        "fetched_at(UTC)/sha256/cached。抓取脚本 code/fetch_*.py 必须可重放。"
        "官方站点抓不到就记\"未验证\"，不许用第三方转载顶替，不许写\"不存在\"。"
        "本次赛题若不需要外部数据，写 NOT-APPLICABLE 并说明附件数据已足够。"),
    "建模架构手": (
        "把题面变成可计算的模型骨架，产出 out/01-model.md：符号表（一符号一义，含单位与量级）、"
        "假设 A1..An（每条标结构性/可检验，并写\"违反了会怎样\"）、目标与约束（写清口径：谁和谁比、分母是什么）、"
        "三处模型脆弱点。所有代码文件写进 code/，结果 JSON 写进 data/。"),
    "求解与优化手": (
        "把模型解出来。必须报告：每次调用耗时（ms）、约束是否在解处起作用（binding 逐来源列，不许只给一个 True）、"
        "解是否在搜索网格边界（边界解必须标星并给出放宽网格后的值）、参数 ±10% 后结论是否翻转。"
        "结果写 data/results_*.json，性质写 out/02-solve.md。"),
    "代理模型训练手": (
        "只在\"精确求解不可行\"时才训练。先用\"单次求解 ms × 需评估次数\"算出必要性；"
        "训练必须留三划分种子、只用训练集标准化、跑 k 折/多种子/外推三件；"
        "GPU 证据必须是训练期每秒采样 nvidia-smi（空闲基线一起报），事后微基准不算。"
        "不需要训练就写 NOT-APPLICABLE 并给出那个乘法。"),
    "数值对账手": (
        "生成 code/verify_numbers.py：把 main.tex 里每个关键数字与 data/*.json 对账，"
        "匹配必须用词边界（`(?<![\\d.])needle(?!\\d)`），否则 \"16\" 会匹配到 \"2016\"。"
        "宣称条数须与实际检查条数一致，任何一条失败就非零退出。结果写 out/03-numbers.md。"),
    "图表手": (
        "图要自解释：单位、样本量、误差带、口径写明在 caption 里；不许用面积代替量值（雷达图禁\"面积即总分\"）；"
        "Laffer/Pareto 必须标拐点；敏感性必须画不利的那一半。图写 figures/*.pdf+png，"
        "生成脚本 code/make_figures.py 可重跑。清单写 out/08-figures.md。"),
    "论文撰写手": (
        "按 templates/PAPER-TEMPLATE.md 的族骨架填正文与摘要。摘要四段式：Background and Task / "
        "Modeling Framework / Results per Question / Validation and Limitation，"
        "至少 3 个数字、关键词与第二段模型名同序、末段必须有一条具体局限。"
        "正文 ≤30 页；页数超了只许把归档表搬附录。正文写到 main.tex，说明写 out/09-writing.md。"),
    "格式合规手": (
        "逐条跑\"不合规就废稿\"的硬项并打勾：前置页顺序（control→summary→contents）、"
        "页眉只有队号+页码、正文 ≤30 页、全英文零汉字、机构名零出现、队号非占位、"
        "参考文献有类型标记且 ≥70% 被引、两遍 xelatex 均 exit 0。用 "
        "scripts\\gauntlet_check.py <论文目录> 一条命令出结论。"),
    "对抗评审手": (
        "扮演不客气的评审，只找能推翻结论的地方：口径错配、结论强于证据、"
        "稳定性只报有利的一半、图表夸大、摘要承诺多于正文兑现。每条给出文件行号与复算命令。写 out/04-review.md。"),
    "创新挖掘手": (
        "找出这篇论文值得拿创新奖的那个点。四类：换表征 / 换约束表达 / 换规模（可扩展性主张）/ 跨学科映射。"
        "必须写成一句可检验命题 + 支撑数字 + 它与\"常规做法\"的差别。没有就写\"只有组合无机制\"并说明缺什么。"),
    "时间与质检手": (
        "倒计时 + 终检，唯一有否决权。算距截止小时数，列\"再不做就废稿\"的项，"
        "跑 gauntlet_check.py 与 verify_numbers.py，给 PASS/FAIL。写 out/06-gate.md。"),
    "调度手": (
        "拆活派活收活，保证交付物之间口径一致。输出四波链与当前卡点，标出谁在等谁，写 out/11-dispatch.md。"),
    "口径审计手": (
        "只查一件事：**同一个词有没有被两种算法用过**。2026_C 的 42 项评审里有 10 项是这个毛病——"
        "「阈值 4.608」和「阈值 4.506」都叫 demand-growth threshold、「ROI 8.81×」和「ROI 5.19×」都叫 ROI、"
        "「闲置 228 m²」在两种布局下分布不同却合成一个数。做法：\n"
        "1) 从 main.tex 抽出所有带单位的量词（增长率/ROI/阈值/份额/闲置/敏感性），列成「词 → 出现行号 → 印的值」；\n"
        "2) 对每个词回 data/*.json 找**唯一**键；找到两个键就是冲突，一个键都没有就是孤儿；\n"
        "3) 每个冲突给「两个数各自的口径 + 建议保留哪一个 + 正文要加哪半句限定」。\n"
        "本项在 APMCM2025_C 与 2026_C 两次评审里都是最高频的真缺陷。写 out/05-caliber.md。"),
    "版式与出栏手": (
        "只查「编译不报错、图看着正常、放大却断头」的那类问题。三件事：\n"
        "1) **图内出栏**：逐张 `figures/*.pdf` 用 pymupdf 取 `get_text(\"dict\")` 的每个 span，"
        "与**图自己的 MediaBox**（416.55 pt 宽）比对，`x1 > W-2.0 or x0 < 2.0 or y1 > H-2.0 or y0 < 2.0` "
        "就是贴边/被裁——注意 `out>0.5` 不够严，matplotlib 会把越界文字裁掉、裁完的 span 恰好止于画布边缘；\n"
        "2) **正文出栏**：`Overfull \\hbox` 逐条回行号，判据是 `>1.0pt` 记账、`>10pt` 必须改；\n"
        "3) **hank/pattern 污染**：`hatch=` 会生成 tiling pattern，BBox 远超画布、视觉被裁但出栏检查数得到，"
        "一律换成 `linestyle=(0,(2.2,1.4))` + `alpha=0.40`。写 out/10-layout.md。"),
    "附录与自指手": (
        "只查「由产物自己决定的值」有没有被手写进正文。三类自指：\n"
        "1) 脚本字节数（`make_figures.py 81,368 B` 这类）——必须由 `code/gen_index.py` 从磁盘现读生成，"
        "`\\input` 进表；手写一次就会在下次改代码时变孤儿 token；\n"
        "2) 自指计数（`36 checks`、`1,704 tokens`、`N claims`）——凡是由 verifier 自己输出的数，"
        "不许写进摘要或正文，因为它下一轮就变；\n"
        "3) 附录 listing 与 `\\lstinputlisting` 的对应关系——每个 `code/*.py` 都要有 listing、"
        "每个 listing 指向的文件都要存在，`paper_source_scope.active_sources` 出 16 个源文件就要有 16 条。"
        "写 out/13-appendix.md。"),
    "流水线运维手": (
        "守流水线本身：`scripts/pipeline.py` 的 s1–s7、`scripts/submission_gate.py` 的九套、"
        "`code/verify_numbers.py` 的不动点、`code/gen_index.py` 的字节数。四件事：\n"
        "1) 跑 `pipeline.py <paper> --status`，把每步状态与每门 PASS/FAIL/?? 抄成表；"
        "`??` 只许出现在 SOFT_GATES（G10 表格数据 / G11 视觉审查 / G14 模板核对）上；\n"
        "2) 任何门 FAIL 时给出「是产物的问题还是门本身的问题」，后者要改 Gate 不是改稿；\n"
        "3) 查 `verify_numbers.py` 是否单次运行即 `failures=0`（自指判据要从决定它自己的那一轮排除，"
        "否则永远不收敛）；\n"
        "4) 改过 `code/make_figures.py` 就必须重跑 `code/gen_index.py`，否则附录 B 的字节数过期。"
        "写 out/14-ops.md。"),
}


_DEPS = {"depends": DEPENDS, "output_of": OUTPUT_OF, "waves": WAVES, "team_id": TEAM_ID}


def use_review_mode(team_id: str) -> None:
    """切到评审队：依赖表、输出表、波次、team_id 全部换掉，其余代码路径不变。

    做成"换表"而不是"复制一份代码"，是因为两队的派单/落地/超时判据必须完全同源——
    上次端到端跑出来的四个判据缺陷，就是这么被两边不同实现放大的。
    """
    from . import review_crew as RC
    _DEPS.update(depends=RC.DEPENDS, output_of=RC.OUTPUT_OF, waves=RC.WAVES, team_id=team_id)
    global DEPENDS, OUTPUT_OF, WAVES, TEAM_ID, TASKS, HOUSE, BRIEF_SQUAD
    DEPENDS, OUTPUT_OF, WAVES, TEAM_ID, TASKS, HOUSE = (
        RC.DEPENDS, RC.OUTPUT_OF, RC.WAVES, team_id, RC.TASKS, RC.HOUSE)
    BRIEF_SQUAD = "review"


def workspace_id_for(path: str | Path) -> str | None:
    """把工作区路径映射成宿主的 workspaceId（state.workspaces 里按 path 精确匹配）。

    宿主的小队定义里 `workspaceId` 是**可选**的（"a squad that pins none runs in the Host
    default session directory"）；不钉，所有小队的 run 都落在同一个默认目录，界面上看就是
    "每支小队的工作区都是一个地方"（2026-11-12 用户第一次指出的现象）。

    **但默认不调用它**。2026-11-12 同一用户的第二次反馈：钉住之后每次派单都会在那个工作区的
    会话列表里新建一条"数学建模评审小队 / 题目契…"，一天就淹掉了正经对话，"都没法找对话了"。
    所以钉工作区是**显式选择**（`create_team(..., workspace_id=...)` / `run_review.py --pin`），
    不是默认行为；文件写入一律靠绝对路径，不依赖会话落在哪个目录。
    """
    root = Path(path).resolve()
    cands = [str(x).lower().replace("/", "\\") for x in (root, *root.parents)]
    js = _js_base() + """
const state = await api(base.base, 'state');
console.log(JSON.stringify((state?.workspaces ?? []).map(w => ({ id: w.id, path: w.path, title: w.title }))));
"""
    for w in json.loads(_node(js)):
        got = str(w.get("path") or "").lower().replace("/", "\\")
        if got in cands:
            return w["id"]
    return None


def create_team(name: str, members: list[dict], description: str = "",
                workspace_id: str | None = "") -> dict:
    """建一个新队并逐人 upsert。members 每项 {name, permission, brief}。

    路由与 body 形状是实测契约：POST team 要 {"team": {...}}，POST member 要
    {"teamId":..., "member": {...}}，exactKeys 严格校验，多一个键就 400。

    `workspace_id` 默认空 = **不钉**（宿主显示"未绑定（用宿主默认目录）"）。理由见
    `workspace_id_for` 的说明：钉住会把每次 run 的会话塞进那个工作区的会话列表，
    一天就淹掉用户自己的对话。要钉就显式传 id。
    """
    js = _js_base() + """
import fs from 'node:fs';
const cfg = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
let state = await api(base.base, 'state');
let team = (state?.teams ?? []).find(x => x.name === cfg.name);
if (!team) {
  const r = await api(base.base, 'team', { method: 'POST',
    body: { team: { name: cfg.name, description: cfg.description || '',
      ...(cfg.workspace_id ? { workspaceId: cfg.workspace_id } : {}) } } });
  team = r.team ?? r;
} else if (cfg.description && (team.description || '') !== cfg.description) {
  // POST /team + {id} 是 in-place 更新（实测：不回 id 就会建重复队）。
  const r = await api(base.base, 'team', { method: 'POST',
    body: { team: { id: team.id, name: team.name, description: cfg.description,
      ...(cfg.workspace_id ? { workspaceId: cfg.workspace_id } : {}) } } });
  team = r.team ?? team;
}
for (const m of cfg.members) {
  const cur = (team.members ?? []).find(x => x.name === m.name);
  // **没有新 brief 时绝不发空串**：2026-11-12 的事故就是"建名册"用了不带 brief 的表，
  // upsert 把 10 个成员的 brief 全清成 0，UI 上看着像一支空队。
  const brief = (m.brief && m.brief.length) ? m.brief : (cur ? (cur.brief || '') : '');
  const body = { teamId: team.id, member: {
    ...(cur ? { id: cur.id } : {}), name: m.name, permission: m.permission } };
  if (brief) body.member.brief = brief;
  await api(base.base, 'member', { method: 'POST', body });
}
state = await api(base.base, 'state');
const t2 = (state?.teams ?? []).find(x => x.id === team.id);
console.log(JSON.stringify({ id: team.id, name: team.name,
  members: (t2?.members ?? []).map(m => ({ name: m.name, permission: m.permission, brief_len: (m.brief||'').length })) }));
"""
    cfg = Path(os.environ.get("TEMP", ".")) / "crew_create_team.json"
    cfg.write_text(json.dumps({"name": name, "description": description, "members": members,
                               "workspace_id": workspace_id or ""},
                             ensure_ascii=False), encoding="utf-8")
    return json.loads(_node(js, str(cfg), timeout=180))


def refresh_team(ws: Path, paper: Path, team_id: str | None = None,
                 workspace_id: str | None = "") -> dict:
    """把**建稿队**的名册与 brief 一起写回（含队伍简介）。

    为什么要有这个函数：`create_team` 只写名册不写 brief 的调用方式（2026-11-12 的
    `run_review.py team`）会把已有 brief 全清空；而 brief 里的路径又会随派单论文变。
    这个函数是"把当前 18 人（评审模式 13 人）的 brief 对齐到 paper"的唯一入口，读完必须报 brief_len。

    `workspace_id` 默认空 = 不钉工作区（2026-11-12 用户要求回到"未绑定（用宿主默认目录）"，
    否则每次派单都在 E:\数学建模 的会话列表里加一条，找不到正经对话）。
    """
    tid = team_id or TEAM_ID
    was = TEAM_ID
    try:
        use_review_mode(tid) if False else None  # 不切模式：建稿队用本模块自己的表
        roster = [n for wave in WAVES for n in wave]
        members = [{"name": n, "permission": PERMISSION.get(n, "workspace-write"),
                    "brief": full_brief(n, ws, paper)} for n in roster]
        got = create_team(TEAM_NAME, members, description=TEAM_DESCRIPTION,
                          workspace_id=workspace_id)
        back = list_members_by_id(got.get("id") or tid)
    finally:
        globals()["TEAM_ID"] = was
    return {"id": got.get("id") or tid, "n": len(back),
            "brief_min": min((m["brief_len"] for m in back), default=0),
            "zero": [m["name"] for m in back if not m.get("brief_len")]}


def list_members_by_id(team_id: str) -> list[dict]:
    """按显式 team_id 读成员（不依赖模块级 TEAM_ID）。"""
    js = _JS_BASE.format(runner=_RUNNER_URI, team_id=team_id) + """
const state = await api(base.base, 'state');
const t = (state?.teams ?? []).find(x => x.id === TEAM_ID);
if (!t) { console.error('team not found'); process.exit(1); }
console.log(JSON.stringify(t.members.map(m => ({ name: m.name, permission: m.permission,
  brief_len: (m.brief || '').length }))));
"""
    return json.loads(_node(js))


def full_brief(name: str, ws: Path, paper: Path, overrides: dict | None = None) -> str:
    """拼一份派单用的 brief。

    优先读 `squads/<main|review>/NN-<成员名>.md`（那是唯一一份手写正文，30 份都在仓库里，
    改了要能被 review 出来）；找不到才回落到 HOUSE+TASKS 的旧拼装。
    两条路径都必须带**当次**的绝对路径：手写正文里写的是上一次的论文目录，
    换题时由这里的三行覆盖掉，不然成员会去读上一题的产物。
    """
    dep = DEPENDS.get(name, [])
    dep_line = "、".join(str(ws / d) for d in dep) if dep else "（无上游依赖，你是本波起点）"
    live = "\n".join([
        f"【本次派单】工作区 {ws}　被测论文 {paper}",
        f"【依赖产物】{dep_line}",
        f"【你的输出】{ws / OUTPUT_OF[name]}",
    ])
    curated = _curated_brief(name)
    if curated:
        return f"{live}\n\n{curated}"
    task = (overrides or {}).get(name) or TASKS.get(name, name)
    problem_pdf = (overrides or {}).get("__problem_pdf__", str(ws / "problem.pdf"))
    body = task.format(workspace=ws, paper=paper, problem_pdf=problem_pdf)
    head = HOUSE.format(ws=ws, paper=paper, py=_pyexe.py())
    return f"{head}\n{dep_line}\n【你的输出】{ws / OUTPUT_OF[name]}\n\n【本次任务】\n{body}"


def _curated_brief(name: str) -> str:
    """找手写 brief：`squads/main/01-题目侦察手.md` 这类文件名按 `NN-名字.md` 编号。"""
    folder = Path(BRIEF_ROOT) / BRIEF_SQUAD
    if not folder.is_dir():
        return ""
    for f in sorted(folder.glob("*.md")):
        if f.stem.split("-", 1)[-1] == name:
            try:
                # rstrip 必须做：宿主收到 brief 会去掉尾部空白，留着换行会让 push 的长度
                # 校验差 1 个字符，报成 MISMATCH（实测 1210 发出去、1209 存回来）。
                return f.read_text(encoding="utf-8").rstrip()
            except OSError:
                return ""
    return ""


def _dec(b: bytes) -> str:
    """node 输出按 UTF-8 解。实测 subprocess 的 text=True 会让中文解成乱码（已放弃该路径）。"""
    return (b or b"").decode("utf-8", "replace")


def _node(script: str, *args: str, timeout: int = 900) -> str:
    proc = subprocess.run(
        # 身份：中文成员名与路径经管道传给 Python 时必须显式 UTF-8，否则按系统 GBK 解出乱码。
        # node 没有 -u 选项（报 bad option: -u）；靠 text=True/encoding 的编解码即可。
        [str(NODE), "--input-type=module", "-e", script, *args],
        capture_output=True, timeout=timeout,  # 读原始 bytes：带 encoding 时线程池解码会把 UTF-8 搅坏
    )
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"node failed ({proc.returncode}): {_dec(proc.stderr or proc.stdout)[:800]}")
    return _dec(proc.stdout).strip()


_RUNNER_URI = "file:///" + str(RUNNER).replace("\\", "/")
_JS_BASE = """
const TEAM_ID = {team_id!r};
const {{ findBase, api }} = await import('{runner}');
const base = await findBase();
"""


def _js_base() -> str:
    """按**当前** TEAM_ID 渲染前缀（切到评审队后不能再吃导入时的旧常量）。"""
    return _JS_BASE.format(runner=_RUNNER_URI, team_id=TEAM_ID)


def list_members() -> list[dict]:
    js = _js_base() + """
const state = await api(base.base, 'state');
const norm = (v) => String(v ?? '').replace(/[^A-Za-z0-9]/g, '').toLowerCase();
const t = (state?.teams ?? []).find(x => x.id === TEAM_ID);
if (!t) { console.error('team not found'); process.exit(1); }
console.log(JSON.stringify(t.members.map(m => ({ id: m.id, name: m.name, permission: m.permission, brief_len: (m.brief||'').length }))));
"""
    return json.loads(_node(js))


def push_briefs(ws: Path, paper: Path, only: list[str] | None = None) -> list[tuple[str, str]]:
    """把每人的 brief 就地更新（POST /member 是 upsert，带 id 即替换）。"""
    js = _js_base() + """
import fs from 'node:fs';
const cfg = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
// 静态 import 只能接字符串字面量，所以 BODIES 用 fs 同步读 JSON（--input-type=module 下可用）。
const BODIES = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const state = await api(base.base, 'state');
const t = (state?.teams ?? []).find(x => x.id === TEAM_ID);
const legacy = { '题目侦察手-补': '题目侦察手' };
const res = [];
for (const m of t.members) {
  const name = legacy[m.name] ?? m.name;
  if (cfg.only && !cfg.only.includes(name)) continue;
  const fb = BODIES[name];
  if (!fb) { res.push([name, 'NO-BODY']); continue; }
  const r = await api(base.base, 'member', { method: 'POST', body: { teamId: t.id,
    member: { id: m.id, name, preset: m.preset ?? 'standard', permission: m.permission, brief: fb } } });
  const got = (r?.team?.members ?? []).find(x => x.id === m.id);
  res.push([name, got && got.brief.length === fb.length ? `OK ${fb.length}` : 'MISMATCH']);
}
console.log(JSON.stringify(res));
"""
    bodies = {m["name"]: full_brief(m["name"], ws, paper) for m in list_members()}
    cfg = Path(ws) / "logs" / "_crew_cfg.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"only": only}, ensure_ascii=False), encoding="utf-8")
    # BODIES 通过临时模块文件传给 node（避免把长中文串塞进 -e 参数）
    body_mod = cfg.with_name("_crew_bodies.json")
    body_mod.write_text(json.dumps(bodies, ensure_ascii=False), encoding="utf-8")
    out = _node(js, str(cfg), str(body_mod).replace("\\", "/"))
    return [tuple(x) for x in json.loads(out)]


def dispatch(ws: Path, paper: Path, members: list[str],
             overrides: dict | None = None) -> dict[str, str]:
    """派一批成员，返回 {成员名: sessionId}。

    overrides: {成员名: 本次任务正文}，只替换被点名成员的 TASKS 段，其余照常。
    实测需要它：8 人并发时 3 人把 240 个工具全花在探索上、一个字节没落盘，
    重派时只改"先落盘骨架再逐节补写"这一句就解决了，不必改 TEAM 级的 brief。

    成员按 **id** 定位，不按名字：中文成员名经 node 到 Python 的管道会被系统
    GBK 解码成乱码，用 id 就绕开整条编码链。
    """
    js = _js_base() + """
import fs from 'node:fs';
const cfg = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const state = await api(base.base, 'state');
const t = (state?.teams ?? []).find(x => x.id === TEAM_ID);
if (!t) { console.error('team not found'); process.exit(1); }
const res = {};
for (const p of cfg.payloads) {
  const r = await api(base.base, 'run', { method: 'POST',
    body: { teamId: t.id, memberId: p.memberId, firstMessage: p.msg } });
  res[p.memberId] = r?.run?.sessionId ?? 'NO-SESSION';
}
console.log(JSON.stringify(res));
"""
    roster = {m["id"]: m["name"] for m in list_members()}
    by_name = {v: k for k, v in roster.items()}
    payloads, wanted = [], []
    for name in members:
        mid = by_name.get(name)
        if mid is None:
            raise KeyError(f"no member named {name!r}; roster={sorted(roster.values())}")
        payloads.append({"memberId": mid, "msg": full_brief(name, Path(ws), Path(paper), overrides)})
        wanted.append(mid)
    cfg = Path(ws) / "logs" / f"_crew_run_{int(time.time())}.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"payloads": payloads}, ensure_ascii=False), encoding="utf-8")
    raw = _node(js, str(cfg).replace("\\", "/"))
    got = json.loads(raw)  # 失败就让异常抛出来：静默吞掉会返回空的派单结果
    return {roster[k]: v for k, v in got.items() if k in wanted}


_LEGACY_NAME = {"题目侦察手-补": "题目侦察手"}


def _to_utf8(s: str) -> str:
    """把被按 GBK 误读的中文还原成真 UTF-8。

    现状：`_node()` 已改为直接对 raw bytes 做 UTF-8 解码，正常情况下用不到
    这个函数。留着是为了修复已经写坏的产物文件名（历史会话里出现过）。
    """
    try:
        fixed = s.encode("gbk").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return fixed if fixed != s and not any(ch == "\ufffd" for ch in fixed) else s


def stamp(ws: Path, members: list[str]) -> dict[str, float | None]:
    """记下派单前每个契约文件的存在时刻，用于区分"真交付"和"建骨架时留下的空壳"。

    为什么要这一步：`new_verify.py` 会补一个 81 B 的 `data/ledger.json`（内容
    `{"records": []}`）。第一次端到端跑就撞上了 —— `landed()` 判它 True，
    而数据溯源手其实**一行都没写**，于是 W0 报"1/2 落地"。判据必须是
    "存在 且 在派单之后被改过"，不是"存在"。
    """
    ws = Path(ws)
    out: dict[str, float | None] = {}
    for n in members:
        p = ws / OUTPUT_OF[n]
        out[n] = p.stat().st_mtime if p.exists() else None
    return out


def _text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _resolve(ws: Path, name: str) -> Path:
    """契约文件的实际位置。

    2026-11-12（实测）：审读员的 cwd 是**工作区根**，而 `OUTPUT_OF` 写的是
    `review/0X.md` 这种相对路径，于是 8 份报告全落在 `review/`，
    而 `outcome()` 去 `PRACTICE_2018A/review/` 找 → 8/8 全报 `missing`，
    实际上 10:55–11:06 已全部交货。判活路径与契约路径必须同源：先看 ws 根，
    再退回任何一个子目录里的同名产物。
    """
    rel = OUTPUT_OF[name]
    p = ws / rel
    if p.exists() and p.stat().st_size:
        return p
    for cand in sorted(ws.glob(f"*/{rel}")):
        if cand.stat().st_size:
            return cand
    return p


def _too_small(ws: Path, name: str) -> str | None:
    """契约文件落地了，但内容明显不是一份真活 —— 返回原因，正常返回 None。

    为什么需要：端到端第一次跑时 `data/ledger.json` 被成员原样留着 81 B 的
    空壳（`{"records": []}`），`landed()` 判 True，W0 就"通过"了。mtime 判据
    能挡住"没动过"的空壳，挡不住"动了一下但没真抓数据"的空壳。所以再按文件
    类型给一条最小内容要求 —— 全部从真实产物反推，不是拍脑袋定的。
    """
    p = _resolve(ws, name)
    if not p.exists() or p.stat().st_size == 0:
        return "文件没生成"  # 让上层能区分"没有"和"有但不算数"
    txt = _text(p)
    if not txt:
        return f"{OUTPUT_OF[name]} 不是 UTF-8 文本或读不出来"
    if OUTPUT_OF[name] == "data/ledger.json":
        try:
            doc = json.loads(txt)
        except json.JSONDecodeError:
            return "data/ledger.json 不是合法 JSON"
        # 台账有两个生产者，键名不同：new_verify.py 写 `records`，
        # ingest_data.py 写 `files`。只认 `records` 会把「已经用 ingest_data.py
        # 正式收进官方数据」的论文判成没干活（2026-11-19 实测 SHUWEI2025_A 即如此）。
        recs = doc.get("records")
        if recs is None:
            recs = doc.get("files", [])
        if not recs:
            # 空 records 有两种：`{"records": []}` 空壳（没干活），和**合法的**
            # NOT-APPLICABLE（题面确实没有外部数字可抓）。后者必须放行，否则
            # 数据溯源手无论怎么认真写都判不落地，s1 会白等满 2400 s。
            # 2026-11-19 实测：题面 20 B、0 个数字 token，成员正确写出
            # status=NOT-APPLICABLE + 5584 B 的理由，landed() 仍 False。
            try:
                doc = json.loads(txt)
            except json.JSONDecodeError:
                return "data/ledger.json 不是合法 JSON"
            na = str(doc.get("status", "")).upper().replace("_", "-")
            why = str(doc.get("not_applicable_line") or doc.get("status_reason") or "")
            if na == "NOT-APPLICABLE" and len(why.strip()) >= 40:
                return None
            return "台账 records 为空，也没写 NOT-APPLICABLE 的理由（只留了 new_verify 的空壳）"
        # 字段名两种都收：`url`（R-M14 的写法）与 `source`（成员实际产出用的键名）。
        # 端到端跑里数据溯源手交了 17 条真记录，却因为用了 `source` 被全判"缺 url"。
        # 判据要盯"有没有可核对的出处"，不是盯某一个键名。
        # `fetched_at`（成员产出）与 `ingested_at`（ingest_data.py 产出）同理。
        bad = [
            r
            for r in recs
            if not (r.get("url") or r.get("source"))
            or not r.get("sha256")
            or not (r.get("fetched_at") or r.get("ingested_at"))
        ]
        if bad:
            return f"{len(bad)} 条记录缺 出处(url/source) 或 sha256 或 fetched_at"
        return None
    # Markdown 类产物：必须写出 VERDICT 行，否则读者无法判断结论
    if "VERDICT:" not in txt:
        return f"{OUTPUT_OF[name]} 里没有 VERDICT: 行"
    bad = _bad_bytes_line(p, txt)
    if bad:
        return bad
    return None


def _bad_bytes_line(p: Path, txt: str) -> str | None:
    """首行 `BYTES n` 与文件真实字节数是否一致 —— 不一致说明成员是"凭印象"写的。

    端到端跑实测：`out/00-problem.md` 31,857 B，首行老老实实写着 `BYTES 00000`。
    它是在建文件之前先写了这一行占位，之后再没回来改。内容是真活，但这种
    自报数字不实，必须查（RUNBOOK §3.3 第 1 项就是查这个）。
    """
    first = txt.splitlines()[0].strip() if txt.splitlines() else ""
    if not first.upper().startswith("BYTES"):
        return None
    try:
        claimed = int(first.split()[1].replace(",", ""))
    except (IndexError, ValueError):
        return f"首行 `{first}` 不是 `BYTES <n>` 形式"
    real = p.stat().st_size  # 必须用文件真实字节：len(txt.encode()) 会把 CRLF 归一化掉，永远相等
    if claimed != real:
        return f"首行自报 BYTES {claimed}，实际 {real}"
    return None


def outcome(ws: Path, name: str) -> str:
    """成员这一轮到底发生了什么：`delivered` / `blocked` / `failed` / `missing`。

    为什么区分：`BLOCKED` 与 `FAIL` 是**契约内的正常回报**，不是"没干活"；
    把它们和"什么都没写"混成一个 False，`run_squad.py` 就会在真正的阻塞点上
    一直等到超时（端到端跑里 W1 就这么白等了 660 s，而它的产物 19:54:42 就写好了）。

    `FAIL` 与 `BLOCKED` 都算"这一波结束，可以进下一波"：成员已经给出了结论，
    该停下来看的是人，不是时钟。
    """
    p = _resolve(ws, name)
    if not p.exists() or p.stat().st_size == 0:
        return "missing"
    if OUTPUT_OF[name] == "data/ledger.json":
        # JSON 台账没有 VERDICT 行，判据是"内容过没过 _too_small 那三道"
        return "delivered" if _too_small(ws, name) is None else "failed"
    txt = _text(p)
    head = "\n".join(txt.splitlines()[:6])
    if "BLOCKED:" in head:
        return "blocked"
    if "VERDICT: FAIL" in txt:
        return "failed"
    if "VERDICT: PASS" in txt:
        return "delivered"
    return "missing"


def landed(
    ws: Path,
    members: list[str],
    since: dict[str, float | None] | None = None,
    strict: bool = True,
) -> dict[str, bool]:
    """契约文件存在、> 0 字节，且（给了 since 时）**在派单之后被写过**。

    实测两次：成员会把内容写进 out/final-check.md 之类**自选文件名**，文件
    17939 B、内容完整、首行还老老实实写了 BYTES 17939 —— 契约文件一个都没有。
    所以判据只能是 OUTPUT_OF 里那一个名字；自选文件名一律算没交付。

    另一次实测：空壳 `data/ledger.json`（81 B）把"没干活"判成"已交付"。
    给了 `since` 就同时要求 mtime 更新，空壳通不过。

    `strict=True` 时再叠加 `_too_small()` 的内容判据。
    """
    ws = Path(ws)
    st: dict[str, bool] = {}
    for n in members:
        p = ws / OUTPUT_OF[n]
        ok = p.exists() and p.stat().st_size > 0
        if ok and since is not None:
            before = since.get(n)
            ok = before is None or p.stat().st_mtime > before
        if ok and strict:
            ok = _too_small(ws, n) is None
        st[n] = ok
    return st


def wait(
    ws: Path,
    members: list[str],
    timeout_s: int = 2400,
    every_s: int = 30,
    since: dict[str, float | None] | None = None,
) -> dict[str, bool]:
    """等到契约文件落地，或超时。超时要**看得见**，不许静默返回全 False。

    实测：`print(f"  ...{...}" + ",".join(...) or "  ...waiting")` 这句在
    没人落地时会退化成 `  ...540s  landed=`，因为 `+` 先于 `or` 求值，空串列表
    拼出来的 falsy 串把 "  ...waiting" 吞掉。看日志的人会以为程序卡死。
    """
    t0 = time.time()
    while True:
        st = landed(ws, members, since)
        if all(st.values()):
            return st
        spent = int(time.time() - t0)
        if spent >= timeout_s:
            missing = [n for n, v in st.items() if not v]
            print(f"TIMEOUT after {spent}s; 未交付: {missing}", flush=True)
            return st
        done = [n for n, v in st.items() if v]
        print(f"  ...{spent:>4}s  landed={done if done else '(none)'}", flush=True)
        time.sleep(every_s)


def wave0(ws: Path, paper: Path) -> list[tuple[str, str]]:
    return push_briefs(ws, paper)