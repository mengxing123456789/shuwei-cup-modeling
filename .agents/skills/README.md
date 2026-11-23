# 技能树

> 六个技能，覆盖「起题 → 建模 → 写稿 → 质检 → 投稿体检」。全部是本机 DSH（DeepSeek Harness）的技能，`skill <name>` 加载，或直接读 `SKILL.md`。

| 技能 | 大小 | 解决什么 |
| --- | --- | --- |
| `mathmodeling/` | 0.78 MB | **主技能**。八步二十门流水线、75 条硬规则、执行手册、排障、语料检索、18 人建稿队 + 13 人评审队 |
| `paper-kit/` | 1.46 MB | 42 个论文质检脚本：投稿格式、写作规则、取 BibTeX、数字溯源、图表视觉审查 |
| `paper-language-pass/` | — | 最小干预润色、压页数、逻辑红线、去 AI 味 |
| `paper-figures-captions/` | — | 架构图提示词、图型选择、caption 写法 |
| `paper-results-review/` | — | 实验数据写成论证段、审稿人视角问题清单 |
| `paper-cn2en-draft/` | — | 中文草稿转英文学术段落 |

## `mathmodeling/` 的结构

```
mathmodeling/
  SKILL.md          20,660 B —— 入口：该用哪个脚本、该读哪份文档
  RULES.md          59,567 B —— 75 条硬规则（E19 环境 / M17 建模 / T6 表格 / W12 写作 / V21 验证）
  WORKFLOW.md       27,566 B —— 八步二十门的完整判据、反模式 P1-a…P6-a
  RUNBOOK.md        42,075 B —— 排障手册、已知故障绕法、时间预算
  CORPUS.md         10,984 B —— 语料怎么查、赛制与题型谱系
  writing.md  modeling.md  THINKING.md  training.md
  scripts/
    pipeline.py      八步定义（STEPS）+ 20 道门（GATES）
    run_all.py       一条命令跑完
    gauntlet_check.py  16 项交稿前总闸
    submission_gate.py 交件前最终体检
    new_paper.py     从 DONOR 骨架起新论文
    corpus_index.py  语料检索
    authenticity_check.py  数据核验
    mmkit/           工具库（见下）
  squads/main/     18 人建稿队 brief
  squads/review/   13 人评审队 brief
  templates/  vendor/  reference/
```

## `mmkit/` 的关键模块

| 模块 | 作用 |
| --- | --- |
| `pyexe.py` | **解释器解析**。顺序 = `MM_PY` → `sys.executable` → `<ws>/envs/mathmodel/python.exe` → `.venv` → `PATH`，且必须能 `import numpy, pandas, matplotlib` 才采用。这是"删光本地环境仍能跑"的关键 |
| `corpus.py` | 语料根解析。`MM_CORPUS_ROOT` → `<ws>/corpus` → 旧的 `AsterLink` 兜底 |
| `gauntlet.py` | 16 项检查的实现（含页号连续性判据：允许目录页后 `\setcounter{page}{1}`） |
| `crew.py` / `review_crew.py` | 18 + 13 人 brief 的模板与拼装 |
| `freshness.py` | 产物与脚本的 mtime 对账 |
| `provenance.py` | 数字溯源 |

## `paper-kit/` 最常用的五个

```powershell
$T = '.agents\skills\paper-kit\tools\run_tool.py'
python $T venue_submission_check.py <论文目录>   # 投稿格式（参数是目录，不是 PDF 路径）
python $T academic_writing_check.py <论文目录>   # 写作规则
python $T paper_data_check.py <论文目录>         # 数字是否都能溯源
python $T scholar_fetch.py <DOI 或标题>          # 取 BibTeX
python $T figure_review.py <figures 目录>        # 图内字号与出栏
```

## 环境变量（都能覆盖默认值）

| 变量 | 作用 |
| --- | --- |
| `MM_PY` | 指定解释器，跳过自动探测 |
| `MM_ROOT` | 工作区根 |
| `MM_CDATA` | 原始数据根（默认 `<ws>/cdata`） |
| `MM_CORPUS_ROOT` | 语料根（默认 `<ws>/corpus`） |
| `MM_C_PROBLEM_ROOT` | 题面附件根（默认 `<paper>/problem/…`） |
