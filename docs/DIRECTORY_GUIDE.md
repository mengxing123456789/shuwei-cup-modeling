# 目录指南

> 这份文件回答一个问题：**每个顶层目录里到底是什么、为什么它在仓库里、什么时候该看它。**
>
> GitHub 的目录列表右侧显示的是「最后一次改动该目录的 commit message」，不是目录说明。想让每个目录显示真实说明，唯一办法是在目录里放 `README.md`——本仓库已经给所有顶层目录放了（见文末清单）。

---

## 一、想干某件事，该看哪个目录

| 我想…… | 去这里 |
| --- | --- |
| 复现 2026 秋季赛 C 题这篇论文 | `_swc2026/SWC2026_C/`（见它自己的 README） |
| 起一道新题，跑八步二十门 | `.agents/skills/mathmodeling/`（`SKILL.md` → `WORKFLOW.md`） |
| 查往年真题 / 一等奖论文 | `corpus/` |
| 知道某个坑怎么绕 | `docs/pitfalls/`（82 条编号坑位） |
| 看这一整套方法论 | `docs/PLAYBOOK.md` |
| 知道什么被排除了、为什么 | `docs/REPO_LAYOUT.md`、`docs/EXCLUDED_LARGE_FILES.md` |
| 看 2025 春季 A 题的完整工程 | `SHUWEI2025_A/` |
| 看 2023 B 题（催化反应）的完整工程 | `PRACTICE_2023B/` |
| 学 modex 商业平台怎么组织流程 | `_modex_re_work/` + `_swc2026/4[4-6]-Modex*.md` |

---

## 二、逐目录说明

### `corpus/` — 历年语料库（456.6 MB / 869 文件）

**这是仓库里唯一权威的语料副本**，原先散在 `C:\Users\29900\Downloads\AsterLink`，已全部导入并压平。

```
corpus/
  problems/<year>/     2019–2025 历年真题题面、附件、官方模板
  awards/<year>/       2019–2025 一等奖论文 PDF，文件名即 <题号><队伍ID>.pdf
  rules/2025/          官方格式规范、承诺书、提交流程、Word 模版
  _extracted_text/2023/ 18 篇 2023 获奖稿的纯文本提取（供 grep）
  _PROVENANCE.md       每份文件的 sha256 与核验判据（OK 9 / SUSPECT 0 / BROKEN 0）
  _DATA-2025.md        2025 A 题官方数据的 sha256 与表结构
```

| 年份 | 一等奖 PDF | 真题/附件文件数 |
| --- | ---: | ---: |
| 2019 | 22 | 8 |
| 2020 | 15 | 186 |
| 2021 | 16 | 20 |
| 2022 | 17 | 427 |
| 2023 | 18 | 4 |
| 2024 | 15 | 59 |
| 2025 | 21 | 16 |

2022 年附件最多（427 个文件，含 `ADNIMERGE_New.csv` 8.07 MB 与 4 题题面）。**没有压缩包**——全部解开、压平、删掉原包。

**为什么不放 `C_Problem_Data`**：三个原始视频包共 5.57 GB（`EgoDemo.zip` 1.82 GB、`EgoPro.zip` 1.84 GB、`EgoStandard.zip` 1.91 GB），赛方官网可重新下载，不值得进 git。它们的下游产物（`panel.npz`、`v3_video_features.csv` 等）也不在仓库里，但**生成它们的脚本在** `_swc2026/SWC2026_C/code/`。

---

### `_swc2026/` — 2026 秋季赛全过程（87.7 MB / 1,829 文件）

```
_swc2026/
  SWC2026_C/            C 题成品工程（论文 + 代码 + 数据 + 审计），见其 README
  SWC2026_A/            弃用的 A 题（25 页英文稿已完成，后改判 C 题）
  SWC2026_B/            弃用的 B 题
  SWC2026_D/            弃用的 D 题
  SWC2026_C_ALT_BACKUP/ 备用稿（用户曾评价"目录做得更好"的那份）
  modex_re/             modex 商业平台的逆向产物（JS bundle、接口、提示词）
  award_corpus_tools/   语料提取与扫描脚本（extract_text.py、_scan1..6.py）
  00-… 到 56-*.md       56 份过程报告（选题 → 建模 → 优化 → 审计 → 提交）
```

**56 份报告的编号规则**：`00`–`09` 选题期，`11`–`32` 建模期，`35`–`42` 第二轮七方向优化，`43`–`56` 格式/审计/AIGC/查重/整体判定。同号的是同批分册（如 `45-Modex逆向-工作流引擎.md` 与 `51-逐问复查与参数核对.md` 编号不同但都叫 45 的那份已改名）。

**`_swc2026/` 根下的 `_*.py` 已清**：从 253 个候选里删了 163 个一次性探针，保留 90 个被报告引用的（判据见 `_repo_tools/prune_root_probes.py`）。

---

### `_swc2026/SWC2026_C/` — C 题成品（本仓库的核心）

```
main.tex                1,655 个 \slot 宏，全部由 data/*.json 生成
slots.tex               生成的宏定义（勿手改）
slots.full.tex          全量版（1,548 条），slots.tex 是它的裁剪版
swmcmthesis.cls/.cfg    官方 LaTeX 模板（改了封面红字居中）
main.pdf                67 页：正文 25 / 附录 42
CSWBMCM2634892.pdf      交付件（= main.pdf + 58 条书签）
CSWBMCM2634892cns.pdf   承诺书（单人，379,731 B）
CSWBMCM2634892fj.zip    支撑材料包（10.36 MB / 480 条目）
code/                   368 个脚本，14 个 stage
data/                   219 个 JSON（数字的唯一来源）
figures/                27 张图
tables/                 18 个 .tex 片段（多数由脚本生成）
audit/                  verify_claims.py（145 条断言）、check_slots.py
problem/                题面 + 官方 7 个附件（自包含，不依赖外部路径）
snippets/reproduce.ps1  一键复现
```

---

### `.agents/skills/` — 可复用技能树（2.3 MB / 175 文件）

| 技能 | 大小 | 是什么 |
| --- | --- | --- |
| `mathmodeling/` | 0.78 MB | **主技能**：八步二十门流水线（`pipeline.py`、`run_all.py`、`gauntlet_check.py`）、75 条硬规则（`RULES.md` 59 KB）、执行手册（`WORKFLOW.md` 27 KB）、排障（`RUNBOOK.md` 42 KB）、语料检索（`CORPUS.md`）、18 人建稿队 + 13 人评审队 brief（`squads/`）、`mmkit/` 工具库 |
| `paper-kit/` | 1.46 MB | 42 个论文质检脚本：`venue_submission_check.py`（投稿格式）、`academic_writing_check.py`（写作规则）、`scholar_fetch.py`（取 BibTeX）、`paper_data_check.py`（数字溯源）、图表视觉审查 |
| `paper-language-pass/` | — | 最小干预润色、压页数、逻辑红线、去 AI 味 |
| `paper-figures-captions/` | — | 架构图提示词、图型选择、caption 写法 |
| `paper-results-review/` | — | 实验数据写成论证段、审稿人视角问题清单 |
| `paper-cn2en-draft/` | — | 中文草稿转英文学术段落 |

**关键模块 `mmkit/pyexe.py`**：解释器解析。顺序 = `MM_PY` 环境变量 → `sys.executable` → `<ws>/envs/mathmodel/python.exe` → `.venv` → `PATH` 里的 `python3`/`python`，且必须能 `import numpy, pandas, matplotlib` 才采用。**这是"删光本地环境仍能跑"的关键**。

---

### `数维杯/` — 备赛资料与官方文件（38.1 MB / 297 文件）

```
00_官网与规则/    2025 + 2026 两套官方件（格式规范 PDF、提交流程、Word 模版、承诺书、LaTeX 模板）
01_往年赛题/      2021–2025 赛题与模板
02_一等奖论文_参考/ 一等奖论文写法提炼.md
03_实战演练/      2021 B 题极端降雨的完整实战
04_评分与复盘/    评分细则_v1.md、自主评分报告_2021B.md、复盘_2021B.md
05_模板与工具/    extract_pdf.py、fetch_ghcn.py、inspect_paper.py、latex/ 骨架
99_归档/          2021B_final（历史收口版）
refs/            official_standard.json（47.9 KB，机器可读的官方规则）
```

**注意 `03_实战演练` 与 `99_归档` 里有 3.96 MB ×2 的同一份 xlsx**，是 2021 B 题附件，故意留两份（一份在演练目录、一份在归档目录），因为两处都需要独立可跑。

---

### `docs/` — 说明书（4 文件 + `pitfalls/` 10 文件）

| 文件 | 内容 |
| --- | --- |
| `PLAYBOOK.md` | **主手册 25.6 KB**：八步二十门表 + 20 道门判据 + C 题全链实测数字 + Modex 逆向要点 + 23 条踩坑 + 官方规则速查 + 15 分钟开赛检查表 |
| `REPO_LAYOUT.md` | 逐目录说明 + 每条 `.gitignore` 规则为什么存在 + 验证命令 + 磁盘占用对照 |
| `EXCLUDED_LARGE_FILES.md` | 被排除的 4 GB 逐项：是什么 / 多大 / 怎么重生成 |
| `DIRECTORY_GUIDE.md` | 本文件 |
| `pitfalls/` | 82 条编号坑位（P-E01…P-E21 环境、P-M01…P-M64 建模、P-W01…P-W15 写作）+ 五族骨架 + 17 条反模式 |

---

### `PRACTICE_2023B/` — 2023 数维杯 B 题（4.0 MB / 168 文件）

催化反应（棉秆热解）。**这是仓库里唯一完整的"练习级"工程**，含 `problem/problem.txt`、`code/`、`data/`、`figures/`、`out/00-problem.md`…`out/15-benchmark.md`、`review/`（13 份审读报告）、`main.tex` + `main.pdf`（30 页）。也充当 `new_paper.py` 的 DONOR（骨架来源）。

---

### `SHUWEI2025_A/` — 2025 春季 A 题（4.9 MB / 61 文件）

完整论文工程，30 页。**注意它根下有 `apmcmthesis.cls/.cfg`**——那是历史遗留的模板文件名（APMCM 与数维杯共用同一套 cls 的早期版本），**不是亚太杯题目**。也充当 `new_paper.py` 的 DONOR 备选。

---

### `_modex_re_work/` — Modex 逆向（1.1 MB / 111 文件）

modex（商业建模工作台）的 JS bundle 解包、接口清单、提示词模板、流程状态机转储。对应三份笔记在 `_swc2026/44-Modex数维杯流程逆向与对标.md`（13.9 KB）、`45-Modex逆向-工作流引擎.md`（63.7 KB）、`46-Modex逆向-技能与质检层.md`（102.4 KB）。**学它怎么把"读题→建模→写稿→质检"做成状态机，是本仓库流水线设计的直接来源。**

---

### `shuwei/` — 早年抓取脚本（17 文件被跟踪）

2023/2024/2025 赛题的抓取与整理脚本（`fetch2023.py`、`p2023{,b,c,d,e}.py`、`p2025{b,c}.py`、`inventory.py`、`scan_ids.py`、`titles.py`、`mk.py`、`readme.py`、`writeall.py`、`check*.py`）。`_src/` 下的三个第三方 `.git` 已被 gitignore 排除。**只保留脚本，抓下来的原始文件已在 `corpus/`。**

---

### `_sw2026/` — 2026 四题原始文本（9 文件）

`2026__ShuWei_Cup_{A,B,C,D}_Problem.txt`（从 PDF 抽的纯文本，供 grep）+ C 题数据集说明 + 论文提交流程 + 论文格式规范 + `extract.py`/`p3.py`。**语料检索的轻量入口**，比在 PDF 里搜快。

---

### `_fixture/` — 流水线冒烟夹具（4 文件）

`main.tex`、`main.pdf`、`code/verify_numbers.py`、`data/results.json`、`logs/fixture.log`。用来测 `pipeline.py` 的 20 道门在最小输入上是否工作。**改门之后跑它，比跑真论文快 100 倍。**

---

### `refs/` — 竞赛通用代码（1 文件被跟踪）

`contest-code/` 里的 `.mat`/`.yuv`/`.bmp`/`.m`/`.exe` 共 6,585 个文件已被 gitignore（5373 个 `.bmp` 是图像序列），只留 `数学建模竞赛中应当掌握的十类算法.pdf`。

---

### `logs/` — 小队运行记录（3 文件）

`_crew_bodies.json`、`_crew_cfg.json`、`_crew_run_1795074891.json`：一次完整的 18 人建稿队派单记录，供研究 brief 怎么拼。

---

## 三、已删除的目录（及原因）

| 目录 | 原大小 | 为什么删 |
| --- | ---: | --- |
| `_swc2026/award_corpus_2025/` | 91.3 MB | 21 篇 PDF 与 `corpus/awards/2025/` **sha256 全同**，扫描脚本已搬到 `_swc2026/award_corpus_tools/` |
| `_swc2026/award_corpus_2023intl/` | 34.2 MB | 18 篇 PDF 与 `corpus/awards/2023/` **sha256 全同**，提取稿搬到 `corpus/_extracted_text/2023/` |
| `SHUWEI2026_C/` 的部分文件 | 2.3 MB | 空骨架 `main.tex`/`swmcmthesis.cls/.cfg`（`main.pdf` 不存在，会干扰 `find_paper()`）+ 7 个与 `_swc2026/SWC2026_C/problem/` **sha256 全同**的附件 |
| `_pkit/` | 33.3 MB | 是 `SWC2026_C/` 的整份拷贝 |
| 163 个 `_swc2026/_*.py` | — | 一次性探针，无任何报告引用 |

---

## 四、顶层目录的 `README.md` 清单

GitHub 目录列表只显示 commit message；要看真实说明，每个目录需要自己的 `README.md`。本仓库已放：

- `corpus/README.md` — 语料结构、年份覆盖、怎么检索
- `_swc2026/README.md` — 56 份报告的编号地图
- `_swc2026/SWC2026_C/README.md` — C 题工程逐文件说明（已有 `README_FJ.md`，此为新写的目录级说明）
- `数维杯/README.md` — 备赛资料的六层结构
- `docs/README.md` — 四份说明书的分工
- `PRACTICE_2023B/README.md`、`SHUWEI2025_A/README.md` — 两份练习工程的题目与结论
- `_modex_re_work/README.md` — 逆向产物索引与三份笔记的对应关系
- `.agents/skills/README.md` — 六个技能各自解决什么

其余目录（`_sw2026`、`_fixture`、`shuwei`、`refs`、`logs`）内容单一，本文件的说明已足够。
