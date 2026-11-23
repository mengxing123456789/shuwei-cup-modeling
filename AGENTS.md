# AGENTS.md — 数学建模工作区总纲

> **这份文件是这个工作区的唯一入口。** 给我一个新题（题面 PDF/文字 + 数据附件），
> 我按 §3 的顺序一路跑到可提交的成稿，中间不停下来问「下一步做什么」。
> 判据不靠「看起来对」：每一步都有机器闸门，闸门不过就停在那里，说清缺什么。

---

## 1. 我在这里的身份与纪律

- **交付物优先于解释。** 先动手（读题、建目录、跑脚本、写文件），再说话。
- **证据优先于叙述。** 任何数字要么来自 `data/*.json`，要么标出处（url + fetched_at + sha256）；
  正文里「我算出来的」中间值一律不许出现。
- **制度文件优先于我的习惯。** 技能正文（`RULES.md` 75 条、`RUNBOOK.md`、`WORKFLOW.md`）
  里写下的判据是踩出来的，不因为「这次特殊」而绕过。
- **不确定就如实说。** 三种结果各自成词：`PASS` / `FAIL` / `NA`（结构上不适用，单独列一行）/
  `??`（该判没判出）。**`??` 不许当 PASS 混过去**（G19 会抓）。
- **改完必验证。** 改脚本 → 跑 `unittest`；改论文 → 重跑 `pipeline.py --status` 与 `gauntlet_check.py`；
  改语料 → 跑 `authenticity_check.py --build`。

---

## 2. 环境事实（照抄，别猜）

| 项 | 值 |
| --- | --- |
| 解释器 | `E:\Mini\envs\mathmodel\python.exe`（3.11.18；numpy/pandas/matplotlib/pymupdf/openpyxl/docx 都在） |
| LaTeX | `E:\MIKTEX\miktex\miktex\bin\x64\xelatex.exe`（用前把 bin 前置到 PATH） |
| 7z | **只有** `C:\Users\29900\AppData\Local\Microsoft\WindowsApps\7z.exe` 这一份；Program Files 那两个路径不存在 |
| DSH Web | 每次重启换端口：读 `$env:DSH_WEB_URL`，不要写死（`_push.py` 已自动探测） |
| 技能根 | `E:\数学建模\.agents\skills\mathmodeling\` |
| 语料根 | `C:\Users\29900\Downloads\AsterLink`（可用 `$env:MM_CORPUS_ROOT` 覆写） |
| 索引 | `E:\数学建模\.mh\corpus.json`；台账 `AsterLink\_PROVENANCE.md` |

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
$SK = 'E:\数学建模\.agents\skills\mathmodeling'
$S  = "$SK\scripts"
```

---

## 3. 新题进来 → 固定动作（一条命令版）

```powershell
# 0) 题面落到 problem/（图片版就先 OCR，扫描件在 G1 会判 FAIL）
# 1) 骨架 + 八步二十门 + 交件，一条命令
& $PY "$S\run_all.py" 'E:\数学建模\<新题目录>' --type C --problem-file '<新题目录>\problem\problem.txt'
# 2) 看状态（可断点续跑：某步 FAIL，修完重跑同一条命令）
& $PY "$S\pipeline.py" 'E:\数学建模\<新题目录>' --status
# 3) 交稿前总闸
& $PY "$S\submission_gate.py" 'E:\数学建模\<新题目录>' --stage final
```

`--type` 选族属（这决定骨架章节与基准带）：

| type | 族属 | 典型题 |
| --- | --- | --- |
| A-α | 物理/信号反演 | 2022A 地震层位、2024A 多普勒测速、2025A 振动抑制 |
| B-α | 过程机理/优化 | 2023B 热解、2020C 除雪、2022B 博弈 |
| C-α | 数据统计/机器学习 | 2021B 降雨、2023C AI 文本检测、2024C 脉冲星噪声 |
| D-α | 评价/决策 | 2020D 复工、2024D 城市韧性、2025C 海岸入侵 |
| E-α | 聚类/时序探索 | 无监督或长序列题 |

**分步版**（要盯某一步、或只重跑一步时）：

```powershell
& $PY "$S\pipeline.py" '<dir>' --step s1        # 只跑一步
& $PY "$S\pipeline.py" '<dir>' --only s5,s6     # 只跑这几步
& $PY "$S\pipeline.py" '<dir>' --force s1       # 已 done 的步骤也要重判（加新门后必做）
& $PY "$S\pipeline.py" '<dir>' --dry            # 只看会派谁、判哪些门，不执行
& $PY "$S\pipeline.py" '<dir>' --skip-dispatch  # 只跑本地门，不派单
```

---

## 4. 八步 · 二十门 · 谁干什么

| 步 | 名称 | 成员 | 门 | 这一步的产出 |
| --- | --- | --- | --- | --- |
| s1 | 赛题分析 | 题目侦察手、数据溯源手、**真题对标手** | G1 G2 **G20** | `out/00-problem.md`（逐句抄出「要求你」）、`data/ledger.json`、`out/15-benchmark.md` |
| s2 | 建模求解 | 建模架构手 | G3 | `out/01-model.md`（每问的模型 + 为什么不是别的） |
| s3 | 编程实现 | 求解与优化手、代理模型训练手、数值对账手 | G4 G5 G10 | `code/`、`data/*.json`、`out/03-numbers.md` |
| s4 | 口径审计 | 口径审计手 | G16 | `out/05-caliber.md`（同一个词不许被两种算法用过） |
| s5 | 图表 | 图表手 | G6 G11 | `figures/*.pdf`、`out/08-figures.md` |
| s6 | 论文撰写 | 论文撰写手、附录与自指手 | G7 G12 G17 | `main.tex`、`out/09-writing.md`、`out/13-appendix.md` |
| s7 | 编译合规 | 格式合规手、版式与出栏手、流水线运维手 | G8 G13 G14 G15 G18 G19 | `main.pdf`、`out/03-compliance.md`、`out/10-layout.md`、`out/14-ops.md` |
| s8 | 评审收口 | 13 人审阅队 | G9 | `review/*.md`（每个审读员一份 + 总编的改进排序） |

门的判据全在 `WORKFLOW.md` §5 与 `pipeline.py` 的 `GATES` 字典里，两边必须一致。
**软门**只有 G10 / G11 / G14（表格数据、视觉审查、模板核对）——它们不阻断，但会出现在 `--status` 的未过清单里。

---

## 5. 每问六件套（写正文的硬骨架）

一问一章，六件齐全才叫闭环：

1. **模型**：变量、假设、方程/目标函数，符号与量纲写全。
2. **求解**：算法名 + 关键参数 + 复杂度或收敛判据。
3. **结果**：数字（带单位）+ 一张图或表，页码对得上。
4. **检验**：残差 / 交叉验证 / 灵敏度 / 边界算例 —— 至少一项，且写明「什么叫通过」。
5. **讨论**：这条结论在什么条件下会失效（写失效条件，不写「模型可以进一步改进」）。
6. **小结**：一句话回答题目问的那件事。

摘要骨架、页数预算、反模式（P1-a…P6-a）在 `WORKFLOW.md` §4、§7。

---

## 6. 真题对标（新题必做，往年怎么解的）

```powershell
& $PY "$S\corpus_index.py" --query-file '<dir>\problem\problem.txt'   # 题面当查询
& $PY "$S\corpus_index.py" --year 2023 --problem B --kind paper --list # 枚举同题论文
& $PY "$S\corpus_index.py" --stats                                     # 语料覆盖情况
```

规则三条，都写在 `CORPUS.md` 里：

1. **先看同题，再看同型。** 同题号永远比字面相似更有信息量（中文查英文论文的 2-gram 重叠接近 0）。
2. **引用语料里的数字必须标「引自已获奖论文 `<队号>`，不是本题结果」** ——否则 G12 抓成未溯源数字。
3. **对标完要下结论**：可照搬三条、照搬会死两条、本题相对最近邻新增的约束三条。

### 数据进 `data/` 只有一条路

```powershell
& $PY "$S\authenticity_check.py" --build                  # 先核：页数/首页字符/表行列数/压缩包条目
& $PY "$S\ingest_data.py" '<dir>' '<下载来的文件>' --source "赛方网盘 A 题"
```

`ingest_data.py` **拒收** `SUSPECT`/`BROKEN`（退出码 1），收下的每份在 `data/ledger.json` 留
sha256 + 判据 + 来源 + `ingested_at`；只有 `--force` 才收得动，但会写 `forced: true`。
G2 数据台账与 G12 论文数字都从这份台账往上对——**没有 ledger 的数字等于没有出处**。

---

## 7. 目录契约（新建论文目录的样子）

```
<论文目录>/
  main.tex  main.pdf  apmcmthesis.cls  cfg  BUILD.md  NO_PEEK.md
  problem/    题面与附件（只读，要清洗另存到 data/）
  data/       所有产物（数字的唯一来源：*.json + ledger.json）
  code/       求解代码 + verify_numbers.py
  figures/    图（pdf 优先，png 备用）
  tables/     表（tex 片段）
  refs/       参考文献与官方格式规范
  review/     所有审读报告（只进这里）
  logs/       pipeline_state.json、briefs/、编译日志
  out/        各成员的法定产物（00-problem.md … 15-benchmark.md）
```

三条硬约定：**产物只进 `data/`**、**报告只进 `review/`**、**`problem/` 只读**。

---

## 8. 小队怎么派（要并发时）

```powershell
& $PY "$S\run_squad.py" '<dir>' --dry        # 先看依赖链
& $PY "$S\run_squad.py" '<dir>'              # 十波，任一波未落地即停
& $PY "$S\run_squad.py" '<dir>' --waves 0-2  # 只跑前三波
```

- 建稿队 18 人十波（`crew.WAVES`），评审队 13 人（`run_review.py`）。
- brief 正文是 `squads/main/NN-*.md`（18 份）与 `squads/review/NN-*.md`（13 份）；
  `crew.full_brief()` 把当次的 `【本次派单】/【依赖产物】/【你的输出】` 三行拼在最前。
- **改 brief 的唯一通道是 `/dsh-agents/api/member`** → 用 `squads\_push.py --write`。
  直接改 `C:\Users\29900\.dsh\dsh-agents\ledger.json` 会被宿主内存副本覆盖，且不报错。
- 派单失败的降级：`logs\briefs\<sN>-<成员>.md` 已落盘，可手工贴给人或当 subagent prompt 发。

---

## 9. 十道禁令（每条都踩过）

1. **别用 `--help` 探参数**：`new_paper.py` / `new_verify.py` / `gauntlet_check.py` 没有 argparse，
   `--help` 会被当成论文目录**真的建出一个叫 `--help` 的目录**。
2. **别用 PowerShell 写 JSON**：`Set-Content` 带 BOM，`json.loads` 会抛 `ValueError: Unexpected UTF-8 BOM`。
   写文件统一用 python `open(..., encoding='utf-8', newline='\n')`。
3. **别写死 GUI 端口**：`$env:DSH_WEB_URL` 是唯一可信来源（重启就变）。
4. **别把成员设成 read-only**：他们要写产物，`read-only` 会让 G1/G9 永远拿不到 VERDICT。
5. **别在正文写「我算出来的」中间值**：G12 要求每个数回到 `data/*.json` 的键。
6. **别让同一个词被两种算法用过**：G16 会抓（「误差」「精度」「R²」尤其常见）。
7. **自指数字不许手写**：页数、字数、图数、表数由产物决定，`附录与自指手` 负责替换（G17）。
8. **`problem/` 只读**：清洗后的数据另存 `data/`。
9. **语料里的数字不是本题结果**：标来源，否则 G12/G20 都会红。
10. **改步骤表必须升 `STATE_SCHEMA`**：已 done 的步骤会被整步跳过（`run_step` 只认 `status=='done'`），
    跳过的步骤**不判它新加的闸门**——新门等于不存在。

---

## 10. 交付判定（三条都要绿）

```powershell
& $PY "$S\gauntlet_check.py" '<dir>'                        # 16 项，退出码 0 = 全过
& $PY "$S\submission_gate.py" '<dir>' --stage final         # gauntlet + venue + 数据/表格/模板/源文件
& $PY "$S\pipeline.py" '<dir>' --status                     # 二十道门
```

`run_all.py` 会自动串完这三条，并把 `main.pdf` 复制成 `<type><队号>.pdf`（队号读 `\baominghao{}`）。

---

## 11. 常见失败与降级路径

| 现象 | 根因 | 怎么办 |
| --- | --- | --- |
| `pipeline.py` 某步一直 FAIL 且说缺文件 | 该成员的会话没落地 | 看 `logs\briefs\`；`--skip-dispatch` 后手工补那份产物再重判 |
| G1 判 FAIL「扫描件」 | 题面是图片 PDF | OCR 或换有文本层的原件；`authenticity_check.py --show` 能看出字符数 |
| matplotlib 崩溃 `0xC06D007F` | 本机已知故障 | 见 `RUNBOOK.md` 的绕法（换后端/换解释器），不是代码问题 |
| 图内字号判 5.98 pt 不过 | `bbox_inches='tight'` + `width=0.86\linewidth` + `Scale=MatchLowercase` | 给到 6.2 pt（留边界） |
| `verify_numbers.py` 不收敛 | 用了文本替换而非不动点循环 | 按 `RUNBOOK.md` §「写文件必须 write_bytes」改 |
| 语料查不到同型题 | 索引过期 / 中文查英文 | 先 `--build`，再用 `--year/--problem --list` 枚举 |

---

## 12. 维护这套流程时（改技能本身）

1. 改 `pipeline.py` 的 `STEPS`/`GATES` → **升 `STATE_SCHEMA`**（会备份旧状态为 `pipeline_state.v<n>.bak`）。
2. 加/删成员 → 同步四处：`mmkit/crew.py`（`DEPENDS`/`OUTPUT_OF`/`WAVES`/`TASKS`/`TEAM_DESCRIPTION`）、
   `squads/MANIFEST.json`、`squads/_push.py`、以及 `tests/`（`test_review_crew.py` 的人数是硬断言）。
   `WAVES` 的**波数固定 10**（`test_runbook.py` 断言），加人放进已有的波，别加波。
3. 改门 → 跑 `--force sN` 才会重判已 done 的步骤。
4. 改完必跑测试：
   ```powershell
   & $PY -m unittest discover -s '.agents\skills\mathmodeling\scripts\tests' -t '.agents\skills\mathmodeling\scripts'
   ```
   基线：**70 tests OK**（2026-11-19 加了 `test_ledger_gate.py` 六条：`ingest_data.py` 的
   `files` 键、合法 `NOT-APPLICABLE`、空壳仍拦、缺 sha256 仍拦）。
5. 加语料 → `authenticity_check.py --build` 再 `corpus_index.py --build`，顺序不能反。

---

## 13. 相关文件（读哪个）

| 要干什么 | 读 |
| --- | --- |
| 完整执行手册、门的判据、反模式 | `WORKFLOW.md` |
| 75 条写作/建模硬规则（E19/M17/T6/W12/V21） | `RULES.md` |
| 排障手册、已知故障绕法、时间预算 | `RUNBOOK.md` |
| 真题语料怎么查、赛制与题型谱系 | `CORPUS.md` |
| 该用哪个技能（论文润色/图表/投稿体检） | `SKILL.md` |
| 小队的 brief 正文 | `squads/main/`、`squads/review/` |

---

## 14. 进行中：数维杯 2026 秋季赛（`_swc2026\`）

> 这一节每次会话都会自动注入。**接手 `_swc2026` 的工作前，先读 `07` 与 `08`。**

| 文件 | 内容 |
| --- | --- |
| `_swc2026\08-C题全面审计与修改纲领.md` | **最新、优先级最高**：899 行 / 50 KB 审计，P0-01…P0-12、P1/P2/P3 逐题、论文层、官方补充通知、模型重构蓝图、执行顺序 |
| `_swc2026\07-C题进展与交接.md` | 进展、文件地图、下一步命令、九条已踩过的坑 |
| `_swc2026\04-选题终局与三天备赛总规划.md` | 四题排序 A>B>D>C、**官方 AI 使用规定**与合规处置、三天时刻表 |
| `_swc2026\audit\verify_claims.py` | 机器校验：当前 **34 项，19 PASS / 15 FAIL**，输出 `audit\verify_claims.json` |

**模型评价暂缓**：等主会话全部跑完再统一评价（2026-11-20 用户指示，勿提前落盘评价文档）。

**主线是 C，不是 A。** A 冻结为备份，不再投入（除非 C 到第 2 天夜里还写不到 15 页才回补）。

三条现状（2026-11-20 20:24 实测，别凭印象）：
1. **C 已成稿但超页**：`main.tex` 1,517 行；`main.pdf` **35 页 / 958,213 B**；`BodyLastPage=26`，**正文超 25 页上限 1 页**；`slots.tex` 1,425 个宏（490 个被引用）。**当前首要任务不是补写作，而是先删回 25 页，再按 `08` 修 P0 口径**——P3 有五个 adaptive/oracle 对象混写，P2 动作空间与官方不一致，AI 合规形式不全。
2. **A 是备份**：`SWC2026_A\main.pdf` 24 页、16/16 门、116 断言 0 失败、已打包。**冻结，不再投入。**
3. **合规通用**：《AI 工具使用情况报告》（Appendix E）无论交哪题都要有，按 C 写；违反官方第⑨条可取消评奖资格。

下一步（按 `08` §10 顺序，别跳）：
```powershell
& 'E:\Mini\envs\mathmodel\python.exe' 'E:\数学建模\_swc2026\audit\verify_claims.py'
# 先修 P0-01/02/03/04（P3 身份与符号）→ P0-07/08（P2 协议/单位）→ P0-09/10/11/12
# 每修一批：fill_numbers.py → xelatex×2 → verify_claims.py
```
判定：`verify_claims.py` 的 FAIL 归零，再谈 §8 的模型重构；重构前不改摘要主叙事。