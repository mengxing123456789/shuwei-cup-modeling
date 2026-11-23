BYTES 2268
# 03 格式合规（数维杯 2026 秋季赛 · 英文赛道）

## 1 官方条款逐条核对（2025 秋季赛规范，2026 模板同义）

| 条款 | 要求 | 本稿状态 | 证据 |
|---|---|---|---|
| 一 | 只能选 A/B/C/D 一题，题号与内容一致 | 通过 | 封面 `Problem Chosen: C`；全文只做 C 题 |
| 二 | 题目/摘要/关键词在第 1 页，第 2 页目录专用 | 通过 | `review_bench` C4：p1 summary=True、p2 contents=True |
| 三 | 每页都有队号与页码 | 通过 | C5：`header lines matched=24`、身份泄露 0；p2 起每页 `Team CSWBMCM2634892 | Page n of 25` |
| 四 | 英文、12 pt、正文 ≤25 页（含摘要与目录） | 通过 | 正文 25 页；`swmcmthesis.cls` 12pt；C7 正文中文 0 |
| 五 | 参考文献按引用次序、方括号编号 | 通过 | 9 条 `\bibitem`，全部带 `[M]`/`[J]`/`[EB/OL]`（C8 markers=9） |
| 六 | 附录含软件名与全部源程序 | 通过 | 附录 B 5 个 `\lstinputlisting`；C9 appendix=True code=True |
| 七 | 正文与附录不得出现身份/学校信息 | 通过 | C5 leaking=0；队号唯一；无姓名/校名/电话 |

## 2 机器检查汇总（现跑）

- `mmkit.review_bench.check_paper`：**11 项 findings，0 项 FAIL**（C4×2、C5×2、C6、C7、C8、C9、C11×3 全过）。
- `submission_gate.py --only venue`：**0 项要你处理**，3 项提醒，4 项通过，1 项不适用。
- `code/page_report.py`：`overfull hbox 0 / undefined 0 / prose numerals 0`。
- 字体嵌入：`pdffonts` 17 个字体全部 `emb=yes`、**Type 3 = 0**、`emb=no = 0`。

## 3 交付件命名

| 件 | 文件 | 字节 |
|---|---|---|
| 论文 | `CSWBMCM2634892.pdf`（= `main.pdf`） | 1,7xx,xxx（见打包记录） |
| 承诺书 | `CSWBMCM2634892cns.pdf` | 单人签名版 |
| 支撑材料 | `CSWBMCM2634892fj.zip` | 源码与结果 |

命名规则：`题号+队伍号`（论文）、`+cns`（承诺书）、`+fj`（支撑材料），与官方提交流程一致。

## 4 提醒（不影响合规）

- 官方 2026 秋季赛通知未在本机，页数/语言按 2025 规范与 2026 模板 demo 的 “at least 12-point, typed in English”；
- 承诺书需手写或电子签名后扫描；
- 提交后需看到系统「已提交」状态。

VERDICT: PASS
