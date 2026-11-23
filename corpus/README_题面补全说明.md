# AsterLink 数维杯资料：完整性说明

整理日期：2026-11-19（第二版）。本说明只描述**这个文件夹里现在到底有什么、哪些核过、怎么查**。

---

## 1. 一句话结论

**2019–2025 七年、每年 A–D 四题，官方题面原件全部到手；85 份文件全部通过真实性核验（OK=85 / SUSPECT=0 / BROKEN=0）。**

- 2023 与 2025 的缺口**已补齐**：`2023_“ShuWei Cup”{A,B,C,D}_Problem.pdf` 与
  `Problem {A,B,C,D}：<英文标题>.pdf` 都在根目录，都是官方原件（不是我复原的整理版）。
- 2025 秋季赛 **D 题不是「缺」**：它是 `Problem D：Modeling and Optimization Research on the Impacts of
  Fukushima Nuclear Wastewater Discharge on the Marine Environment.pdf`（4 页，官方原件）。
- 早先那批「据优秀论文反推」的题面整理版 md **已全部删除**——反推件与原件混在一起是最坏的组合：
  读起来都对，追来源全断。只保留了 `2025年数维杯秋季赛题目\2025_ShuWei Cup A_Problem（中文译稿）.md`（纯翻译，供快速读题）。

---

## 2. 目录里有什么

```
AsterLink\
  2019_“ShuWei Cup”IMCM_Problem.zip          2019数维杯…优秀论文.zip
  2020_“ShuWei Cup”IMCM_Problem .zip        2020数维杯国际赛优秀论文集.zip
  2021_“ShuWei Cup”IMCM_Problem .zip        （2021 论文为散装 PDF，16 篇）
  2022“ShuWei Cup”_Problem.rar              2023第九届…优秀论文.zip（含一份 (1) 副本）
  2024“ShuWei Cup”_Problem.zip（内套一层 zip） 2025年数维杯秋季赛优秀论文.zip（A12/B4/C5，无 D）
  2023_“ShuWei Cup”{A,B,C,D}_Problem.pdf    ← 官方原件
  Problem A/B/C/D：<英文标题>.pdf            ← 2025 秋季赛官方原件
  2023 附录：Appendix I-Compound Helicopter….xlsx
             Annex I / II-Pyrolysis….xlsx（B 题两张表）
             1、Appendix I-ScienceNet Articles.xlsx
             3、Appendix III-Articles with AI-generated…docx
             4、Appendix IV-Models and Pictures.docx
             1、Annex I-Table of Contaminant Quantity….xlsx … 4、Annex IV-…xlsx（D 题四张表）
  2025 A：Problem A：Data.xlsx（3 表：系统参数 12×4、场景1 1002×6、场景2 1002×2）
  承诺书 / Word 模版 / 格式规范 / 提交流程（2025 秋季赛，pdf+docx）
  _PROVENANCE.md                             ← 逐份核验台账（sha256 + 页数/表结构 + 来源判定）
  .asterlink-cache\manifest.json             ← 同一份台账的机器可读版
```

---

## 3. 怎么核的（判据不是「看起来像」）

| 类型 | 判据 | 不通过的后果 |
| --- | --- | --- |
| PDF | pymupdf 能开、页数>0、首页可抽字符 ≥200 | <200 且有页数 = 扫描件，模板与数字提取会失败（判 SUSPECT） |
| xlsx | 至少一张表且 `max_row ≥ 2` | 只有表头 = 数据没下全 |
| docx | 段落字符 ≥100 或含表格 | 空文档/占位模板 |
| zip | 条目>0，并递归一层嵌套 zip | 2024 题目包是 zip 套 zip，不递归会只看到 2 条题面 |
| rar | `7z l -ba` 行数>0 | 7z 只在 `…\WindowsApps\7z.exe` 这一份 |

复跑：

```powershell
$PY='E:\Mini\envs\mathmodel\python.exe'
$S='E:\数学建模\.agents\skills\mathmodeling\scripts'
& $PY "$S\authenticity_check.py" --build     # 重建台账 + _PROVENANCE.md
& $PY "$S\corpus_index.py" --build           # 重建检索索引
```

---

## 4. 怎么查（给新题找最近邻）

索引 195 条，落在 `E:\数学建模\.mh\corpus.json`：

| 年 | 题面 | 论文 | 备注 |
| --- | --- | --- | --- |
| 2019 | 6 | 22 | 题面含承诺书/格式规范 2 份 |
| 2020 | 10 | 15 | 题面含数据说明与模板 |
| 2021 | 8 | 16 | |
| 2022 | 12 | 17 | A 题随题有 402 个地震 txt（未索引单个 txt） |
| 2023 | 4 | 18 | + 6 份附件（xlsx/docx） |
| 2024 | 9 | 15 | |
| 2025 | 5 | 21 | + A 题 Data.xlsx；无 D 题论文 |

```powershell
& $PY "$S\corpus_index.py" --query-file <论文目录>\problem\problem.txt   # 题面当查询
& $PY "$S\corpus_index.py" --year 2023 --problem B --kind paper --list    # 枚举同题论文
& $PY "$S\corpus_index.py" --stats                                        # 覆盖情况
```

用法与题型谱系（七年四类题的族属规律）写在 `E:\数学建模\.agents\skills\mathmodeling\CORPUS.md`。

---

## 5. 还缺什么（如实记）

1. **2025 秋季赛 B/C/D 的官方数据**：B 要 >30000 张、61 类作物病害图（官方只发题面）；
   C 要官方 `datasets 1–9`；D 未见随题附件。**逐题结论见 [`_DATA-2025.md`](_DATA-2025.md)**——
   只有 A 题 `Problem A：Data.xlsx` 是官方件且核过（sha256 记在台账里）。
2. **2024 A/B/C 的数据附件**：题面未随附可下载的表，指标需从题面给定范围与公开数据推。
3. **2022 A 的地震数据**：`Seismic Data` 目录下有 402 个 txt，索引只收了说明 PDF（单 txt 没意义）。
4. **标题字段是启发式**：28 条题面里 20 条标题可读，剩下 8 条会退化成摘要首句或被页宽截断
   （2020A/D、2021A–D、2024A/B/D）。**`year` + `problem` + `kind` 是准的**，按题号检索不受影响。

---

## 6. 补题的历史（留作记录）

- 官方站 `nmmcm.org.cn` 2026 年改版，旧文章已清，题目一律走百度网盘（无直链 PDF）。
- 2025 A 最早是从 GitHub 镜像拿到的官方英文 PDF；2023 四题与 2025 B/C/D 当时只能靠「公开解题文章 +
  本地优秀论文的 Problem Restatement」复原。
- 现在这些官方原件都由用户从网盘下载到本目录，**复原版已删除**，台账里 `source_status` 全部标「官方原件」。