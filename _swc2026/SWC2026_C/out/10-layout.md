BYTES 1550
# 10 版式与出栏（读者看不见的地方）

## 1 页面事实（`code/page_report.py` 现算）

| 项 | 值 | 判据 |
|---|---|---|
| 正文页数 | 25 | 官方上限 25（含摘要页与目录页） |
| 附录页数 | 33 | 官方：附录不限 |
| 总页数 | 58 | — |
| Overfull hbox | **0** | 任何 >1pt 的溢出一律记账，>10pt 必改 |
| Undefined references | **0** | 无 `??` 交叉引用 |
| Prose numerals | **0** | 正文没有裸数字（全部走 `\slot*` 宏） |

## 2 图表出栏

- `figures/*.pdf` 共 6 个，逐个用 `pymupdf` 比对**图自己的 MediaBox**（`x1 > W+4pt` 等判据）：0 处越界。
- 图内字号：`figfont` 6 个 PDF 全部 `ok=True`、`violations=0`（`min=5.98pt` 是单字符下标，判据只数 ≥3 字符）。
- 表格：20 张表，最宽的一张（`tab:p2grid`）在 `\footnotesize` + `tabcolsep` 调整后无溢出。

## 3 页眉页脚

- 摘要页 `\thispagestyle{empty}`，不显示页码；第 2 页起 `\rhead{Team CSWBMCM2634892 \quad Page \thepage\ of \pageref{BodyLastPage}}`。
- 实测 p2 文本首行 `Team CSWBMCM2634892 | Page 2 of 25`；附录段 `\rhead{Appendix, p.\,\thepage}` 与正文区分。

## 4 视觉审查（G11）

6 张图逐张送视觉模型；本轮 5 张有结论、1 张因上游限流记 `unverified`（工具按设计不把未审记成通过）。该门是**软闸门**，不影响编译与提交，但图内文字重叠类问题仍需人工看一眼——本稿 5 张已审图的结论是无重叠、无截断。

VERDICT: PASS
