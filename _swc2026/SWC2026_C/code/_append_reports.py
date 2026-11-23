# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(r".\_swc2026")

p47 = ROOT / "47-备用稿与获奖论文对比评估.md"
s = p47.read_text(encoding="utf-8")
s = s.replace("现有闸门：`page_report` body 25 / appendix 41 / overfull 0 / undefined 0；`verify_claims` 145 PASS；`verify_numbers` 136；`gauntlet` 16/16",
              "现有闸门：`page_report` body 25 / appendix 42 / overfull 0 / undefined 0；`verify_claims` 145 PASS；`verify_numbers` 136；`gauntlet` 16/16")
s = s.replace("`SWC2026_C\\snippets\\reproduce.ps1`（83 行，当前只覆盖第一轮）",
              "`SWC2026_C\\snippets\\reproduce.ps1`（可移植；默认全链，`-Full` 覆盖第二轮）")
s += """

---

## 10. A/B/C 全套执行结果（2026-11-22 20:45 更新）

- **A1 图**：正文插图 7 → **10 张**（framework、P1 pipeline、stage timeline、boundary score、value ladder 等），达到 48 篇获奖稿的中位 10 张。
- **A2 文字**：正文仍 **25 页**（正文 25 / 附录 42 / 总 67）；新增 Assumptions、Data insight、Sensitivity 与三张图后仍守住官方上限。
- **A3 假设**：§2.4 新增 8 条编号 Assumptions，指向 Appendix J 登记表。
- **C1/C2/C3**：三问各加 `Data insight` 段；§6.1 新增 `Sensitivity of the two decision layers`（两段，引用 Appendix K）；§1.2 已有三问链叙述并重绘 Figure 1。
- **B1 去硬编码**：`code/common.py` 的 ROOT/PROJ 改为由 `__file__` 推导，支持 `MM_ROOT` / `MM_CDATA` / `MM_C_PROBLEM_ROOT` 覆盖；39 个脚本的绝对路径已批量清理并逐个通过 `compileall`。
- **B2 复现入口**：`snippets/reproduce.ps1` 重写为可移植（`MM_PYTHON` / `MM_TEXBIN`），默认跑主链，`-Full` 跑第二轮链；解压到空目录实测可重编译（67 页、undefined 0）。
- **B3 环境**：`requirements.txt` 固定 numpy 2.4.6 / pandas 3.1.1 / scipy 1.17.1 / scikit-learn 1.9.1 / torch 2.14.1 / matplotlib 3.11.2。
- **B4 数据清单**：`data/derived_manifest.json` 记录 **165 个派生 JSON** 的 bytes + sha256（7,548,369 B 合计）。
- **B5 文档**：`README_FJ.md` 重排为 stage 1–14，修正 626 个槽（full 1,655）与 352 个脚本。
- **闸门**：`page_report` body 25 / appendix 42 / total 67 / overfull 0 / undefined 0 / prose numerals 0；`verify_claims` **145 PASS**；`verify_numbers` **136**；`check_slots` **626 defined / 618 used / 8 unused / 0 undefined**；`gauntlet` **16/16 PASS**。
- **交付件**：`CSWBMCM2634892.pdf` **2,475,316 B / 67 页**；`CSWBMCM2634892cns.pdf` 198,274 B；`CSWBMCM2634892fj.zip` **12,695,666 B / 558 条目 / 14.66 MB**。

**结论**：原先“呈现层下四分位”的短板已补到获奖稿中位（正文 10 图、正文 25 页）。剩余差距主要是文字密度仍偏高与附录体量，不属于结构性缺陷；技术贡献与可复现性仍是本稿的最强项。
"""
p47.write_text(s, encoding="utf-8")

p43 = ROOT / "43-官方格式核对与图表重做.md"
s = p43.read_text(encoding="utf-8")
s += """

---

## 补充：A+B+C 展示与复现改造（2026-11-22，m20168）

按 `47-备用稿与获奖论文对比评估.md` 的 A/B/C 清单全部执行：

| 项 | 结果 |
| --- | --- |
| A1 正文图 | 7 → **10 张**；新增 `fig_p1_pipeline.png`（drawio 导出）、`fig_stage_timeline.png`、`fig_boundary_score.png`，价值阶梯图从 Appendix K 迁入 §6 |
| A2 页数 | 正文仍 **25 页**，附录 42 页，总 67 页 |
| A3 假设 | §2.4 新增 8 条 Assumptions |
| C1/C2/C3 | 三问 Data insight；§6.1 Sensitivity 小节；§1.2 三问链叙述 |
| B1 | `code/common.py` 去硬编码，39 个脚本绝对路径清理 |
| B2 | `snippets/reproduce.ps1` 可移植 + `-Full` 第二轮链 |
| B3 | `requirements.txt` 固定版本 |
| B4 | `data/derived_manifest.json` 覆盖 165 个派生 JSON |
| B5 | `README_FJ.md` stage 1–14、626 槽（full 1,655）、352 脚本 |

复跑结果：`page_report` 正文 25 / 附录 42 / 总 67 页，overfull 0 / undefined 0 / prose numerals 0；`verify_claims` 145 PASS / 0 FAIL；`verify_numbers` 136 / 0；`check_slots` 626 defined / 618 used / 0 undefined；`gauntlet_check` 16/16 PASS。交付件：PDF 2,475,316 B、承诺书 198,274 B、支撑包 12,695,666 B / 558 条目、合计 14.66 MB。解压到空目录后 `xelatex` 两遍实测 67 页、undefined 0。
"""
p43.write_text(s, encoding="utf-8")
print("appended")
