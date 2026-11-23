# `.agents/skills/` — 六个技能 + 流水线引擎

这个仓库能复用的核心不是 C 题论文，而是这里的技能树。论文只是它跑出来的一个产物。

## 六个技能

| 技能 | 干什么 | 什么时候加载 |
| --- | --- | --- |
| `mathmodeling` | **主力**：八步二十门流水线、75 条写作规则、语料检索、图表字体检查、评审小队 | 任何建模任务 |
| `paper-kit` | 42 个离线质检脚本 + 10 家期刊格式注册表 + 13 份 DOCX 版式档案 | 成稿前体检、格式对齐、DOCX 导出 |
| `paper-figures-captions` | 架构图提示词、图型选择、caption 写法 | 画方法图、选图型、写图表注 |
| `paper-language-pass` | 最小干预润色：润色、长度微调、逻辑红线、去 AI 味 | 成稿后逐段加工 |
| `paper-cn2en-draft` | 中文草稿 → 英文学术段落（含中文回读 + 改动日志） | 中文思路写成英文正文 |
| `paper-results-review` | 把实验数据写成有论证链的段落；审稿人视角出问题清单 | 写结果段、投稿前挑毛病 |

## `mathmodeling` 的骨架

```
mathmodeling/
  SKILL.md          入口：该用哪个技能
  RULES.md          75 条硬规则（E19/M17/T6/W12/V21 五族）
  WORKFLOW.md       八步二十门的判据与反模式
  RUNBOOK.md        排障手册、已知故障绕法
  CORPUS.md         语料怎么查、赛制与题型谱系
  writing.md        写作规范
  modeling.md       建模规范
  THINKING.md       动手前的自检清单
  training.md       备赛训练
  scripts/          mmkit 引擎 + 20 道门 + 小队派单
  squads/main/      18 份建稿队 brief
  squads/review/    13 份评审队 brief
  templates/        论文骨架
  reference/        历年 handoff 与算法速查
```

## `mmkit` 关键模块（写脚本时 import 这些）

| 模块 | 作用 |
| --- | --- |
| `mmkit.paths` | `Paper` 对象：`ws` / `paper` / `code` / `data` / `figures` / `out` / `review` / `logs` |
| `mmkit.pyexe` | **解释器发现**：`py()` / `resolve_py()` / `mupdf_py()`，按 `MM_PY` → `sys.executable` → `envs/mathmodel` → `.venv` → `PATH` 顺序探测 |
| `mmkit.corpus` | 语料索引：`corpus_root()` / `load()` / `query()` / `snippet()` / `stats()`；`_rebase()` 把索引里的相对路径拼回当前根 |
| `mmkit.crew` | 建稿队 18 人的 `DEPENDS` / `OUTPUT_OF` / `WAVES` / `TASKS` / `full_brief()` |
| `mmkit.review_crew` | 评审队 13 人的同款结构 |
| `mmkit.gauntlet` | 16 项格式判据（页数、页眉、字号、图注、身份泄漏） |
| `mmkit.freshness` | 产物新鲜度：脚本比产物新 = stale |
| `mmkit.authenticity` | 数据真实性核验（页数、字符数、表行列数） |

## 五个环境变量（换机器时设这些）

| 变量 | 作用 | 不设的后果 |
| --- | --- | --- |
| `MM_PY` | 指定 Python 解释器 | 自动探测，可能选到缺 numpy 的裸 python |
| `MM_ROOT` | 指定工作区根 | 从脚本位置向上找 `.agents/skills` |
| `MM_CDATA` | 指定 C 题原始数据目录 | 默认 `<root>/cdata` |
| `MM_CORPUS_ROOT` | 指定语料根 | 默认 `<root>/corpus` |
| `MM_C_PROBLEM_ROOT` | 指定 C 题官方附件目录 | 默认 `<paper>/problem/...` |

## 为什么 brief 用中文写

`crew.py` 的 `HOUSE` 模板与 18 份 brief 都是中文。原因是这些 brief 是给**中文语境的模型**读的指令，中文能写得更紧（同样的约束中文比英文短 30%）。产物语言（论文）仍是英文，两件事分开。

## 加技能的规矩

新技能放 `.agents/skills/<name>/SKILL.md`，第一段必须写清「什么时候该用我」，否则模型选不中。技能目录名与 `SKILL.md` 里的 `name:` 字段必须一致。
