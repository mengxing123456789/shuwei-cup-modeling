# 归档说明：备用稿审读脚手架（2026-11-21 22:2x）

本目录存放从 `E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP` **移出**的过渡性审读脚手架。
移出而非删除，目的是保留全部证据链，同时让「提交工作区」和 `CSWBMCM2634892fj.zip` 支撑材料
不含任何打开往届一等奖语料的可运行脚本、也不含引用该语料的临时日志。

## 为什么移出

- `code/check_no_peek.py`（练习赛防偷看自检，非 20 门之一）原先报 4 处 FAIL：
  - `logs/_review_bodies.json`、`logs/_review_run_1795254190.json`、`logs/_review_run_1795254612.json`
    —— 命中的是 **s7 评审 brief 里「禁止引用一等奖语料」这句指令本身**（含 `_award_pdfs.json` 字样），
    不是答案。
  - `out/_figcheck/award_figref.py` —— 用户 m10786 / m01825 明确要求「与一等奖论文对账」时的
    图表 base-rate 统计脚本，会打开 `E:\数学建模\APMCM-PROBLEMS\_award_text\`。
- 这些是**过程脚手架**，不是建模正文、不是交付件、不含获奖答案进入论文。论文 `main.tex` / `main.pdf`
  全文零 `_award_*` 引用、CJK=0、所有数字由 `code/alt_*.py` 现算。
- 但 `code/package_alt.py` 会把 `out/` 整个打进 `fj.zip`，`_figcheck` 不在跳过条件里 →
  会随支撑材料提交一个「读往届获奖语料」的脚本。这既不专业也无须用于复现任何数字，故移出。

## 内容

- `logs/`：4 个 s7 评审运行的 brief / 结果 JSON（临时编排日志）。`logs/pipeline_state.json`
  是 20 门状态文件，**保留**在原工作区。
- `out/_figcheck/`：28 个图表审读工作台文件（几何量测、字号、patch 报告、4 张当时 74 页稿的
  页面 PNG、sensitivity/VOI 探针脚本）。这是历史审读证据，不是复现材料。

## 保留在交付工作区的相关证据

- `review/07-figures.md`：图表审读报告（历史稿，已在文首标注「历史审读记录」）。
  其中对往届一等奖论文的 figure-caption base-rate 统计是用户明确要求的对账工作，
  属合法文献综述；`check_no_peek.py` 的 `SKIP` 含 `review`，按设计不扫这类评审批注。
- 移出后 `code/check_no_peek.py .` → `VERDICT: PASS`（0 hits），且负对照仍成立：
  植入一行 `_award_text` 路径即 `FAIL`，删掉恢复 `PASS`。

## 未改动

- 主稿 `E:\数学建模\_swc2026\SWC2026_C` 全程未动（用户 m11017 指令）。
- `main.tex` / `main.pdf` / 三件套内容未因本次移出改变；仅 `fj.zip` 少了审读脚手架条目。
