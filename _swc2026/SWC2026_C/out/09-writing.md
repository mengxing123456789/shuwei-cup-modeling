BYTES 2457
# 09 论文撰写：成稿形态与逐项检查（SWC2026 C）

## 1 交付形态（现算）

| 项 | 值 |
|---|---|
| 语言 / 字号 | English / 正文 12 pt（`swmcmthesis.cls` 12pt 基准） |
| 正文页数 | **25**（`BodyLastPage`，官方上限 25，含摘要页与目录页） |
| 附录页数 | 33（官方：附录不限） |
| 总页数 | 58 |
| 源文件 | `main.tex` 101,771 B；`slots.tex` 173,040 B；`tables/*.tex` 6 个 |
| 图表 | 5 个 figure 环境 / 6 张图；20 张表；4 个编号公式 |
| 参考文献 | 9 条，全部带 `[M]`/`[J]`/`[EB/OL]` 类型标记 |

## 2 结构（正文 8 节 + 附录 7 节）

正文：1 Introduction → 2 Data and Problem Setting → 3 Problem 1: State and Observation Reliability (Part I) → 4 Problem 2: Prediction under Missing Observations (Part II) → 5 Problem 3: Stochastic Scheduling (Part III) → 6 Empirical Decision Limits of the Task → 7 Model Evaluation → 8 Conclusion。
附录：A Notation → B Key code → C Reproduction commands → D Closed-form calibration → E Annotation audit and unseen task classes → F The chain in one picture → G Second-round experiments。

三问各有一节，节内都有 `Answer to Problem k` 收口段；第 6 节回答“这套数据到底能把决策推到哪”，第 7 节集中报误差与失败案例。31 个 subsection。

## 3 机器检查（全部现跑）

- `mmkit.review_bench.check_paper`：**11 项 findings，0 项 FAIL**（C4 摘要页/目录页、C5 页眉 24 行命中且 0 身份泄露、C6 页数、C7 正文中文 0、C8 类型标记 9、C9 附录与源码、C11 队号/参考文献）。
- `code/page_report.py`：`overfull hbox 0 / undefined 0 / prose numerals 0`。
- `code/verify_numbers.py`：`109 claims passed, 0 failed`；机器可读行 `claims=109 declared=109 checked=109 failures=0 verdict=PASS`。
- `main.log`：两遍 `xelatex` 均 exit 0，无 `!`。

## 4 写作约定（本轮遵守）

1. 摘要页只放 Summary + 关键词，不放目录；第 2 页只放 Content。
2. 每个结果类数字都绑定 `slots.tex` 的宏，不手写；正文不出现工具自指计数（如“109 claims”）。
3. 图注只写图上真有的东西；表注写清单位与口径。
4. 论断分级：能由数据支持的写“we find”，属建模选择的写“we assume / we choose”，不把假设写成发现。
5. 失败与边界单列（第 7 节），不藏在附录。

VERDICT: PASS
