# 数维杯 2026 秋季赛 · 第一轮四题尝试（索引）

> 本目录是一次「四题全做、再选题」的完整尝试。结论：**选 A 题**。

## 先读哪两个文件

1. **`01-四题第一轮总报告.md`** — 四题各做了什么、硬结果、复验记录、下一步。
2. **`02-选题建议与评分矩阵.md`** — 七维评分（A 8.08 / B 7.40 / C 6.51 / D 5.33）、三段修订记录、逐题风险编号。

## 四题目录

| 题目 | 目录 | 主要产物 |
|---|---|---|
| A（建议选） | `SWC2026_A/` | `main.pdf`（24 页）、`ASWBMCM2634892.pdf`、`out/00–15`、`data/` 8 JSON、`figures/` 8 组、`tables/` 12 |
| B | `SWC2026_B/` | `out/00,01,03,15`、`data/` 6 JSON、`figures/` 9、`code/verify_numbers.py`（128 断言） |
| C | `SWC2026_C/` | `out/00,01,03,15`、`data/` 9 JSON、`figures/` 8 |
| D | `SWC2026_D/` | `out/00,01,03,15`、`data/` 6 JSON、`figures/` 26 |

## A 题提交件（已生成）

- `SWC2026_A/ASWBMCM2634892.pdf`：正文 24 页（≤25），全英文，官方 `swmcmthesis` 模板，页眉 `Team ASWBMCM2634892` / `Page x of N`。
- `SWC2026_A/ASWBMCM2634892cns.pdf`：承诺书（1 页，已填 A 题/队号/学校/队长，打印后手写签名）。
- `SWC2026_A/ASWBMCM2634892fj.zip`：支撑材料（main.tex、code/、data/、figures/、tables/、out/、review/）。

## 复现（A 题）

```bash
cd SWC2026_A
python code/p1_mechanistic.py
python code/p2_shape.py
python code/p3_decline.py
python code/p4_econ.py
python code/p5_sobol.py
python code/make_paper_tables.py
python code/make_paper_figures.py
python code/verify_numbers.py     # 116 claims, 末行 failures=0
pdflatex main.tex && pdflatex main.tex
```

## 证据分级

- **L1**：主控（lead）自己实跑的脚本，原始输出与 JSON 均留档。
- **L2**：子代理实跑 + 主控用独立实现复现（差异 <1%）。
- **L3**：子代理结果未经独立复算，只在报告里作为参考、不进结论。

## 环境备注

- Python：`E:\Mini\envs\mathmodel\python.exe`（3.11.18，已修复 numpy 2.4.6 的 `numpy.libs` 缺失导致的 `0xC06D007F` 崩溃）。
- LaTeX：`E:\MIKTEX\miktex\miktex\bin\x64\xelatex.exe` / `pdflatex`。
- 语料：`C:\Users\29900\Downloads\AsterLink`（仅数维杯往年优秀论文；未使用亚太杯资料）。

---

## 新增（2026-11-20 16:50）

| 文件 | 内容 |
| --- | --- |
| `07-C题进展与交接.md` | C 题进展、文件地图、下一步命令、九条已踩过的坑 |
| `../AGENTS.md` §14 | 三条现状，**每次会话自动注入**（跨会话告知靠这一节） |

> 模型评价暂缓：等主会话全部跑完再统一评价（2026-11-20 用户指示）。

## 新增（2026-11-21 13:40）

| 文件 | 内容 |
| --- | --- |
| `44-Modex数维杯流程逆向与对标.md` | Modex 3.0.2 的数维杯 7 步真实契约（`aris.db.workflow_steps.output_files`）、商业闸门、引擎级后检、与本地 8 步 20 门对照、C 题按七步逐项核验、数据/视频全量审计边界 |
