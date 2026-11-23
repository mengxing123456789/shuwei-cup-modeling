# SWC2026_C — 数维杯 2026 秋季赛 C 题成品工程

> **Restocking 人形机器人：手部状态、掩码预测与再观测调度。** 67 页论文（正文 25 / 附录 42），队号 `SWBMCM2634892`，交付件 `CSWBMCM2634892.pdf`。

## 一分钟复现

```powershell
# 只要一个装了 numpy/pandas/matplotlib 的 Python 和 MiKTeX
cd _swc2026\SWC2026_C

python code\fill_numbers.py       # 从 data/*.json 生成 slots.tex（1,655 个宏）
xelatex main.tex                  # 第一遍
xelatex main.tex                  # 第二遍（目录与交叉引用）
python code\add_pdf_outline.py    # 写 58 条书签（PyMuPDF）
python code\verify_numbers.py     # 136 条数值不变量 → 期望 0 failed
python code\page_report.py        # 期望 body 25 / overfull 0 / undefined 0
```

已用 `git clone --depth 1` 到空目录实测：**四个命令全部通过，产出 67 页 PDF。**

## 目录

| 路径 | 内容 |
| --- | --- |
| `main.tex` | 主文件，107 KB，1,655 个 `\slot*` 宏 |
| `slots.tex` | 生成的宏定义（574 条，**勿手改**） |
| `slots.full.tex` | 全量版 1,548 条，`slots.tex` 是它的裁剪版 |
| `swmcmthesis.cls/.cfg` | 官方 LaTeX 模板（改了封面红字居中、`\lstset` 边距） |
| `main.pdf` / `CSWBMCM2634892.pdf` | 67 页 / 2,590,705 B，含 58 条书签 |
| `CSWBMCM2634892cns.pdf` | 承诺书，单人，379,731 B |
| `CSWBMCM2634892fj.zip` | 支撑材料包，10.36 MB / 480 条目 |
| `CSWBMCM2634892.docx` | 供查重/AIGC 网站用的 DOCX（**不是提交件**） |
| `code/` | 232 个脚本，14 个 stage |
| `data/` | 219 个 JSON —— **数字的唯一来源** |
| `figures/` | 27 张图（正文 6 张，其余在附录） |
| `tables/` | 18 个 `.tex` 片段，多数由 `code/make_*.py` 生成 |
| `audit/` | `verify_claims.py`（145 条结构断言）、`check_slots.py`（槽覆盖审计） |
| `problem/` | 题面 + 官方 7 个附件（**自包含**，不依赖 `AsterLink`） |
| `snippets/reproduce.ps1` | 一键复现脚本 |

## code/ 的 14 个 stage

| stage | 脚本 | 产出 |
| --- | --- | --- |
| 1 数据 | `data_inventory.py`、`p1_badtype.py` | `data/*.json` 清单 |
| 2 P1 状态 | `state_layer.py`、`p1_state.py`、`p1a_gpu_segmentation.py` | `panel.npz`、`state.npz`、分割分数 |
| 3 P1 可靠性 | `up2_p1b_v2.py`、`p1b_loto.py` | V1–V8 检测器、LOTO |
| 4 P2 预测 | `p2_predict.py`、`p2_official_distance.py` | ridge / 分位 GRU / 官方 mean R |
| 5 P3 调度 | `p3_schedule.py`、`p3_stochastic_schedule.py` | EDF / slack / 冻结策略 |
| 6 第二轮优化 | `up2_*.py`、`up3_*.py`、`up4_*.py`、`up5_*.py`、`up6_*.py` | 七方向对照 |
| 7 消融 | `up7_p2_context.py`、`up8_p2_features.py`、`up9_p3_sensitivity.py` | context / feature / OAT |
| 8 设计 | `up10_p1_keypoint_loo.py`、`up11_p1_stage_threshold.py`、`up12_p3_full_factorial.py` | LOO / 阈值 / 2^7 全因子 |
| 9 代表点与三水平 | `up13a…`、`up13b…`、`up13c…`、`up14_p3_three_level.py` | 三锚重训 / 3^5 设计 |
| 10 复现性 | `up15_p1a_final_repeats.py`、`p1a_final_decode.py` | P1 头条分布口径 |
| 11 官方指标 | `up16…`、`up17…`、`up18_p2_timing.py` | P3 十一项 scorecard |
| 12 图表 | `remake_body_figures.py`、`make_phase_figure.py`、`make_value_figure.py`、`make_framework_figure.py`、`make_chain_figure.py`、`make_video_figure.py` | 全部图 |
| 13 附录生成器 | `make_appendix_{g,k,l,m,n,n_p1p3}.py`、`make_table_loto.py` | `tables/*.tex` |
| 14 打包 | `package.py`、`add_pdf_outline.py` | 三件交付物 |

## 论文结构

正文 8 章（25 页）：1 Introduction（含 Problem analysis + Figure 1 链路图）· 2 Data and Problem Setting（含 8 条 Assumptions）· 3 Problem 1（状态 + 可靠性）· 4 Problem 2（掩码预测）· 5 Problem 3（调度）· 6 Empirical Decision Limits（含价值阶梯 + 敏感性）· 7 Model Evaluation（预注册门槛 + 未达标项）· 8 Conclusion。

附录 15 节（42 页）：A Notation · B Key code · C Reproduction commands · D Closed-form calibration · E Annotation audit · F The chain · G Second round · H Three algorithms · I Three propositions · J Assumptions · K Sensitivity · L Official scorecard · M Parameter register · N Ablation and check register · O Validation notes。

## 闸门（改任何东西之后都跑）

```powershell
python code\verify_numbers.py                          # 136 条不变量
python audit\verify_claims.py                          # 145 条结构断言
python audit\check_slots.py                            # 槽覆盖（0 undefined）
python '..\..\.agents\skills\mathmodeling\scripts\gauntlet_check.py' .   # 16 项
```

## 三个设计决定

1. **数字只从 `data/*.json` 出**：`fill_numbers.py` 把每个数字变成 `\slot*` 宏，正文里手写的数字会被 `page_report.py` 的 prose-numeral 检查抓出来。
2. **P1 头条报分布不报点**：训练循环不是逐位可复现（chunked sampling + cuDNN autotuning），所以报 3 次重训的 `0.5366 ± 0.0124`，并明写「初稿的 0.5487 是偏乐观的抽样」。
3. **负结果全部进附录**：视频融合 +0.0008%、10 Hz 劣于 2 Hz、付费复核 0 格过 1 pt、RL −0.94 pt，都在 Appendix N 有编号条目。

## 依赖

Python 3.11 + numpy 2.4.6 / pandas 3.1.1 / scipy 1.17.1 / scikit-learn 1.9.1 / torch 2.14.1 / matplotlib 3.11.2 / PyMuPDF；LaTeX 用 MiKTeX（xelatex）。详见 `../../requirements.txt`。
