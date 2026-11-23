# 数维杯数学建模 · 可复用工作区

> 2026 年第十二届数维杯（秋季赛）C 题的完整作战记录，加上为此搭起来的一整套**可迁移流水线**：技能树、八步二十门、数字溯源、格式闸门、评审小队，以及把商业工作台（Modex）逆向出来的契约对照。

**这个仓库是自包含的。** 克隆下来之后不需要任何外部路径、任何本地原始数据、任何其他项目目录——所有脚本用 `mmkit/pyexe.py` 和 `_corpus_root()` 自动定位解释器与语料，两个环境变量（`MM_PY`、`MM_CORPUS_ROOT`）可以覆盖。

---

## 两条路，别混

这个仓库支持两件完全不同的事，命令不通用：

### A. 复现 C 题这篇论文（已实测通过）

```powershell
git clone https://github.com/mengxing123456789/shuwei-cup-modeling.git
cd shuwei-cup-modeling\_swc2026\SWC2026_C

# 只需要一个装了 numpy/pandas/matplotlib 的 Python + MiKTeX
python code\fill_numbers.py       # 1,655 个宏，从 data/*.json 生成 slots.tex
xelatex main.tex                  # 第一遍
xelatex main.tex                  # 第二遍
python code\add_pdf_outline.py    # 58 条书签（需 PyMuPDF；缺了会给出安装提示，编译不受影响）
python code\verify_numbers.py     # 136 条数值不变量 → 期望 0 failed
python code\page_report.py        # 期望 body 25 / overfull 0 / undefined 0
```

**已在空目录 `git clone --depth 1` 实测**：以上命令全部 rc=0，产出 **67 页 PDF**（正文 25 + 附录 42），`verify_numbers` 报 `136 claims passed, 0 failed`。

### B. 起一道新题（跑八步二十门）

```powershell
cd .agents\skills\mathmodeling

# 先在 <新题目录> 里放 problem\problem.txt
python scripts\run_all.py <新题目录> --type C --cls swmcm --skip-dispatch
python scripts\pipeline.py <新题目录> --status          # 断点续跑看门禁
python scripts\submission_gate.py <新题目录> --stage final
```

- `--skip-dispatch` **必须加**，否则它会派单给 DSH Web 小队（需要 `DSH_WEB_URL`，没有就挂住）。
- `--cls swmcm` 用数维杯官方模板；`apmcm` 用亚太/美赛模板。
- `--type` 决定骨架章节与基准带：`A` 物理/信号反演、`B` 过程机理/优化、`C` 数据统计/机器学习、`D` 评价/决策、`E` 聚类/时序探索。

**已在空目录实测**：自动建出 `main.tex`、`swmcmthesis.cls/.cfg`、`code/verify_numbers.py`、`refs/official_standard.json`、`logs/pipeline_state.json`，然后正确停在 `s1` 并报「缺 `out/00-problem.md`」——因为没放题面，这是对的行为。

### C. 只想查往年真题 / 一等奖论文

```powershell
python .agents\skills\mathmodeling\scripts\corpus_index.py --stats
python .agents\skills\mathmodeling\scripts\corpus_index.py --year 2023 --problem B --kind paper --list
```

语料在 `corpus/`（456.6 MB / 869 文件，2019–2025 共 124 篇一等奖 PDF + 720 份真题与附件）。

---

## 环境

| 需要 | 说明 |
| --- | --- |
| Python 3.11 + numpy / pandas / scipy / scikit-learn / matplotlib | `MM_PY` 可指定；否则自动探测 `sys.executable` → `<ws>/envs/mathmodel/python.exe` → `.venv` → `PATH` |
| PyMuPDF（`fitz`） | 只有写书签与图表字号检查需要 |
| MiKTeX（xelatex） | 编译论文；`snippets/reproduce.ps1` 会自动找 |
| 7-Zip / NanaZip | 只有解带中文名的压缩包需要（Python `zipfile` 处理 GBK 成员名会乱码） |

详见 [`requirements.txt`](requirements.txt)。

---

## 仓库地图

| 路径 | 是什么 | 有用吗 |
| --- | --- | --- |
| [`.agents/skills/mathmodeling/`](.agents/skills/mathmodeling/) | **主流水线**：`SKILL.md` 入口、`WORKFLOW.md` 八步二十门判据、`RULES.md` 75 条硬规则、`RUNBOOK.md` 排障、`CORPUS.md` 语料检索、`scripts/`（`pipeline.py`/`gauntlet_check.py`/`submission_gate.py`/`mmkit/`）、`squads/` 18 人建稿队 + 13 人评审队 | ★★★ |
| [`.agents/skills/paper-kit/`](.agents/skills/paper-kit/) | 42 个离线质检脚本 + 10 家期刊格式注册表 + 40 套竞赛流水线定义 | ★★★ |
| `.agents/skills/paper-{language-pass,figures-captions,results-review,cn2en-draft}/` | 润色/去 AI 味、图型与图注、结果段与审稿、中英互译 | ★★★ |
| [`corpus/`](corpus/) | **历年真题与一等奖论文**（2019–2025，124 篇 PDF + 720 份真题/附件），已压平去重 | ★★★ |
| [`_swc2026/SWC2026_C/`](_swc2026/SWC2026_C/) | **C 题成品工程**：论文 + 232 脚本 + 219 JSON + 审计 | ★★★ |
| [`_swc2026/`](_swc2026/) | 2026 秋季赛全过程：A/B/D 题探索、56 份过程报告、Modex 逆向三件 | ★★★ |
| [`数维杯/`](数维杯/) | 官方规则与模板（2025+2026）、往年赛题、一等奖写法提炼、评分复盘、模板工具 | ★★★ |
| [`docs/`](docs/) | 四份说明书 + 82 条编号坑位 | ★★★ 先读 |
| [`PRACTICE_2023B/`](PRACTICE_2023B/) | 2023 B 题（棉秆热解）完整练习，含 13 份审读报告 | ★★ |
| [`SHUWEI2025_A/`](SHUWEI2025_A/) | 2025 春季 A 题工程，含 12 篇一等奖对标审计 | ★★ |
| [`_modex_re_work/`](_modex_re_work/) | Modex 商业平台逆向（DB schema、提示词模板、状态机） | ★★ |
| `SHUWEI2026_C/` | 2026 C 题早期副本（已被 `_swc2026/SWC2026_C` 取代） | ★ 存档 |
| `shuwei/` | 早年抓取脚本 | ★ 存档 |
| `_sw2026/` | 2026 四题纯文本（grep 用） | ★ |
| `_fixture/` | 流水线冒烟夹具（改门之后跑它） | ★★ |
| `refs/` | 十类算法 PDF（竞赛代码大件已排除） | ★★ |

**四份必读**：

- [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) — 主手册 25.6 KB：八步二十门表 + 20 道门判据 + C 题全链数字 + Modex 逆向要点 + 23 条踩坑 + 15 分钟开赛检查表
- [`docs/DIRECTORY_GUIDE.md`](docs/DIRECTORY_GUIDE.md) — 每个目录里到底是什么、为什么在仓库里
- [`docs/REPO_LAYOUT.md`](docs/REPO_LAYOUT.md) — 每条 `.gitignore` 规则为什么存在
- [`docs/EXCLUDED_LARGE_FILES.md`](docs/EXCLUDED_LARGE_FILES.md) — 被排除的 3.2 GB 是什么、怎么重生成

---

## C 题成品

| 文件 | 说明 |
| --- | --- |
| `CSWBMCM2634892.pdf` | **提交稿**：67 页（正文 25 + 附录 42），全英文，58 条书签，页眉 `Team CSWBMCM2634892 / Page x of 25` |
| `CSWBMCM2634892cns.pdf` | 承诺书（1 页，单人，379,731 B） |
| `CSWBMCM2634892fj.zip` | 支撑材料（480 条目 / 10.36 MB），解压后可独立重编译 |
| `main.tex` / `slots.tex` | 源文件；正文所有数字都是 `\slot*` 宏，由 `fill_numbers.py` 从 `data/*.json` 生成 |
| `audit/verify_claims.py` | 145 条结构断言 |
| `code/verify_numbers.py` | 136 条数值不变量 |

题目：Restocking 人形机器人（Part I 手部状态与观测可靠性 / Part II 掩码预测 / Part III 预约调度）。

**核心结论**：掌心坐标系做手状态（`ARI 0.5366 ± 0.0124`，比 Ward 高 12.28 点）→ 预测在 0.30 s 处越过"直接观测"的成本交叉点 → 「按预测时长预留 + EDF」把准时率抬 `+5.38` 点（CI `[2.57, 8.18]`），而"付费二次观测"在 270 个格子里 0 格值得买。价值阶梯：规则值 25.28/21.88 点，真实时长只值 3.33/3.85 点——**准时率是规则买来的，不是数据买来的**。

---

## 三条纪律

1. **数字只有一个来源。** 正文不许手写结果数字；所有数字是 `slots.tex` 里的宏，由 `fill_numbers.py` 从 `data/*.json` 生成，`audit/check_slots.py` 检查"有没有未定义槽 / 有没有裸数字"。
2. **断言分层。** 结构层 145 条（`verify_claims.py`）+ 数值层 136 条（`verify_numbers.py`）+ 格式层 16 项（`gauntlet_check.py`）+ 单元测试 70 条。任何一层红，就不算完成。
3. **负结果照写。** 视频对强检测器无增益（AP `+0.0008%`）、付费复核 270 格 0 格通过、10 Hz 采样劣于 2 Hz、P1 训练不可逐位复现（所以头条报三次重训的 `mean ± sd`）——全在正文和附录里。

---

## 关于内容授权

`corpus/awards/` 是**其他参赛队的获奖论文 PDF**，仅作本地写法对标用。要开公开仓库，建议先把它移出或保持 private。

技能树里 `paper-*` 四个技能改编自 [Leey21/awesome-ai-research-writing](https://github.com/Leey21/awesome-ai-research-writing)（该仓库无 LICENSE，故为结构级重写改编，详见 [`.agents/skills/README.md`](.agents/skills/README.md)）。
