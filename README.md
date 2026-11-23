# 数维杯数学建模 · 可复用工作区

2026 年第十二届数维杯（秋季赛）C 题的完整作战记录，加上为此搭起来的一整套**可迁移流水线**：技能树、八步二十门、数字溯源、格式闸门、评审小队、以及把商业工作台（Modex）逆向出来的契约对照。

目标只有一个：**下一届再打数维杯时，不用从零开始。**

仓库：<https://github.com/mengxing123456789/shuwei-cup-modeling>（private）

```powershell
git clone https://github.com/mengxing123456789/shuwei-cup-modeling.git 'E:\数学建模'
```

---

## 30 秒上手

```powershell
# 1. 环境（Python 3.11 + 科学栈；LaTeX 用 MiKTeX）
$PY = 'E:\Mini\envs\mathmodel\python.exe'          # 或改成你的解释器
$SK = 'E:\数学建模\.agents\skills\mathmodeling'      # 技能根

# 2. 拿一道新题，一条命令起骨架 + 八步二十门 + 交件
& $PY "$SK\scripts\run_all.py" 'E:\数学建模\<新题目录>' --type C --problem-file '<新题目录>\problem\problem.txt'

# 3. 看门禁状态（可断点续跑）
& $PY "$SK\scripts\pipeline.py" 'E:\数学建模\<新题目录>' --status

# 4. 交稿前总闸
& $PY "$SK\scripts\submission_gate.py" 'E:\数学建模\<新题目录>' --stage final
```

`--type` 决定骨架章节与基准带：`A-α` 物理/信号反演、`B-α` 过程机理/优化、`C-α` 数据统计/机器学习、`D-α` 评价/决策、`E-α` 聚类/时序探索。

---

## 仓库地图

| 路径 | 是什么 | 现在还有用吗 |
|---|---|---|
| `.agents/skills/mathmodeling/` | **主流水线技能**：`SKILL.md`（入口）、`WORKFLOW.md`（八步二十门判据）、`RULES.md`（75 条硬规则）、`RUNBOOK.md`（排障）、`CORPUS.md`（真题语料检索）、`scripts/`（`pipeline.py`、`gauntlet_check.py`、`submission_gate.py`、`mmkit/`）、`squads/`（18 人建稿队 + 13 人评审队 brief） | ★★★ 直接复用 |
| `.agents/skills/paper-kit/` | 42 个离线检查脚本 + 10 家期刊格式注册表 + 40 套竞赛流水线定义（含数维杯） | ★★★ 直接复用 |
| `.agents/skills/paper-{language-pass,figures-captions,results-review,cn2en-draft}/` | 句子与图表层面的四个手活技能（润色/去 AI 味、图型与图注、结果段与审稿、中英互译） | ★★★ 直接复用 |
| `_swc2026/` | **2026 秋季赛 C 题主战场**：`SWC2026_C/`（论文工程）、A/B/D 题第一轮尝试、55 篇过程报告、Modex 逆向三件 | ★★★ 主参考 |
| `数维杯/` | 官方规则与模板（2021/2025/2026 三套）、往年赛题与数据、一等奖论文写法提炼、复盘与评分细则、模板工具 | ★★★ 常备 |
| `PRACTICE_2023B/` | 2023 数维杯 B 题（催化反应）完整练习 | ★★ 练手 |
| `SHUWEI2025_A/` | 2025 秋季赛 A 题旧工程（含 12 篇一等奖对标审计） | ★★ 参考 |
| `SHUWEI2026_C/` | 2026 C 题早期副本（已被 `_swc2026/SWC2026_C` 取代） | ★ 存档 |
| `shuwei/` | 2022–2023 早年尝试与抓取脚本 | ★ 存档 |
| `_modex_re_work/` + `_swc2026/modex_re/` | Modex 3.0.2 逆向工作目录（字符串表、zlib 解包、DB schema） | ★★ 想再挖时用 |
| `refs/` | 十类算法 PDF + 竞赛代码（MATLAB/YUV 等大件已排除） | ★★ 参考 |
| `docs/` | **本仓库的说明书**（见下） | ★★★ 先读 |

`docs/` 里三份必读：

- [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) —— **复用手册**：八步二十门怎么跑、技能清单、C 题完整技术链路与关键数字、Modex 逆向要点、20 条踩过的坑。
- [`docs/REPO_LAYOUT.md`](docs/REPO_LAYOUT.md) —— 目录逐项说明 + 每条 `.gitignore` 规则为什么存在。
- [`docs/EXCLUDED_LARGE_FILES.md`](docs/EXCLUDED_LARGE_FILES.md) —— 被排除的大文件清单，以及每个怎么重新生成。

---

## 2026 秋季赛 C 题成品（`_swc2026/SWC2026_C/`）

| 文件 | 说明 |
|---|---|
| `CSWBMCM2634892.pdf` | **提交稿**：67 页（正文 25 + 附录 42），全英文，58 条 PDF 书签，页眉 `Team CSWBMCM2634892 / Page x of 25` |
| `CSWBMCM2634892cns.pdf` | 承诺书（1 页，签名版） |
| `CSWBMCM2634892fj.zip` | 支撑材料（480 条目 / 10.36 MB）：`main.tex` + `slots.tex` + `code/` + `data/` + `tables/` + `figures/` + `problem/` |
| `main.tex` / `slots.tex` | 源文件；**正文里所有数字都是宏**（`\slotXxx`），由 `code/fill_numbers.py` 从 `data/*.json` 生成 |
| `code/` | 200+ 脚本，全链可重跑；`snippets/reproduce.ps1` 一键复现 |
| `data/` | 所有实测产物（JSON 为唯一数字来源） |
| `audit/verify_claims.py` | 145 条结构断言（正文说的每件事都能回到 JSON） |
| `code/verify_numbers.py` | 136 条数值不变量 |
| `logs/` | 训练与编译日志 |

题目：Restocking 人形机器人（Part I 手部状态与观测可靠性 / Part II 掩码预测 / Part III 预约调度）。

**核心结论**（一句话版）：手状态用掌心坐标系（`ARI 0.5366 ± 0.0124`，比 Ward 高 12.28 点）→ 预测在 0.30 s 处越过"直接观测"的成本交叉点 → 调度上"按预测时长预留 + EDF"把准时率抬 `+5.38` 点（CI `[2.57, 8.18]`），而"付费二次观测"在 270 个格子里 0 格值得买。价值阶梯：规则值 25.28/21.88 点，真实时长只值 3.33/3.85 点，**准时率是规则买来的，不是数据买来的**。

---

## 三条纪律（这套东西为什么可信）

1. **数字只有一个来源。** 正文不许出现手写结果数字；所有数字是 `slots.tex` 里的宏，由 `fill_numbers.py` 从 `data/*.json` 生成，`audit/check_slots.py` 检查"有没有未定义槽 / 有没有裸数字"。
2. **断言分层。** 结构层 145 条（`verify_claims.py`）+ 数值层 136 条（`verify_numbers.py`）+ 格式层 16 项（`gauntlet_check.py`）。任何一层红，就不算完成。
3. **负结果照写。** 视频对强检测器无增益（AP `+0.0008%`）、付费复核 270 格 0 格通过、10 Hz 采样劣于 2 Hz、P1 训练不可逐位复现（所以头条报三次重训的 `mean ± sd`）——这些全在正文和附录里，不在"讨论与展望"里糊过去。

---

## 关于内容授权

`_swc2026/award_corpus_2025/` 与 `award_corpus_2023intl/` 是**其他参赛队的获奖论文 PDF**，仅作本地写法对标用。要开公开仓库，建议先把这两个目录移出或把仓库设为 private。

技能树里 `paper-*` 四个技能改编自 [Leey21/awesome-ai-research-writing](https://github.com/Leey21/awesome-ai-research-writing)（该仓库无 LICENSE，故为结构级重写改编，详见 [`.agents/skills/README.md`](.agents/skills/README.md)）。
