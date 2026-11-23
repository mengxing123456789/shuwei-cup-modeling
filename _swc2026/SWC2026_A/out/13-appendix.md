# 附录与自指核对（A 题）

VERDICT: PASS

## 1. 附录结构

`main.tex` 末尾有四个附录，均以 `\section*{Appendix ...}` 起排并进入目录：

- **Appendix A — Code inventory**：按文件列出 13 个 Python 源文件及其职责，不印行号与字节数（避免手写自指数字）。
- **Appendix B — NPV and golden-vector code**：`lstlisting` 内联 `p4_econ.py` 的 `materials()` 与 `test_b4()`（`breaklines=true`）。
- **Appendix C — Mass-balance check**：内联质量守恒校验代码，对应正文 §3 的 $7.66\times10^{-5}$。
- **Appendix D — Reproduction commands**：从 `p1_mechanistic.py` 到 `pdflatex` 的完整复现命令序列。

## 2. 自指数字的生成方式

所有「页数、图数、表数、参考文献数」均由 PDF 与源文件实测，不手写：

| 项目 | 实测值 | 核对方式 |
|---|---|---|
| 总页数 | 24 | `pymupdf` 读 `main.pdf` 页数；页眉 `Page x of 24` 与之一致 |
| 正文页数（至 Appendix A 前） | 23 | 页眉分子在 Appendix A 首页变为 23 |
| 图 | 5 幅（fig_schematic / fig_scaling / fig_shape / fig_npv / fig_pareto） | `grep -c '\begin{figure}' main.tex` |
| 表 | 12 张（`tables/tab_*.tex` 全部 `\input`） | `grep -c '\input{tables' main.tex` |
| 参考文献 | 12 条 | `grep -c '\bibitem' main.tex` |
| 摘要段数 | 5 段 | 人工核对，与 §1–§6 一一对应 |

## 3. 数字与代码的绑定

- 正文中每一个带单位的数值都来自 `data/*.json`；`code/verify_numbers.py` 共 116 条断言，末行输出 `failures=0`。
- 表文件由 `code/make_paper_tables.py` 从 JSON 直接生成，生成后不再手改；本轮仅调整字号、列宽与表头缩写，未改任何数值。
- 图由 `code/make_paper_figures.py` 从 JSON 生成，文件名与正文 `\includegraphics` 一一对应。

## 4. 一致性检查

- 摘要、§5、§6、§8 中出现的 Case 1/2/3 最优浸泡时间统一为「连续口径 9.8 / 23.5 / 35.4 d；五日设计网格 10 / 25 / 35 d」，Table 10 注明两者差 ≤1.5 d。
- Case 3 峰值 NPV $+184.3\times10^4$ CNY 在摘要、§5、§6、§8 四处一致。
- 盈亏平衡数字（11.5 倍、2.13 倍、35,417、6,840 CNY/m³、$-600.2$、$-325.4\times10^4$ CNY）只在 §6 与 §8 出现，均与 `p4_econ.break_even` 一致。
- 全文无姓名、学校、致谢等身份信息；图表内无中文；正文 CJK 字符数为 0（附录亦为 0）。
