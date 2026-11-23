# PRACTICE_2023B — 2023 数维杯 B 题（棉秆热解催化反应）

> 仓库里唯一完整的**练习级**工程：从题面到 30 页论文，走完八步二十门，含 13 份审读报告。也充当 `new_paper.py` 的 DONOR（骨架来源）。

## 题目

`problem/problem.txt` 首行：

```
===== page 1 =====
2023_"ShuWei Cup"
Problem B：The catalytic reaction of cotton stalk pyrolysis
```

棉秆热解催化反应：给定温度程序与产物收率，建模反应动力学、求活化能、优化升温策略。

## 结构

```
PRACTICE_2023B/
  problem/      题面与附件（只读）
  code/         求解脚本 + verify_numbers.py
  data/         所有产物（数字的唯一来源）
  figures/      图
  tables/       表（.tex 片段）
  out/          00-problem.md … 15-benchmark.md（各步法定产物）
  review/       13 份审读报告（06-code.md、04-fit.md 等）
  refs/         参考文献与官方格式规范
  logs/         pipeline_state.json
  main.tex      论文源文件
  main.pdf      453,859 B / 30 页
```

## 为什么留它

1. **它是 `new_paper.py` 的骨架来源**：`DONOR_CANDIDATES = (WS/"PRACTICE_2023B", WS/"SHUWEI2025_A")`，要求目录同时含 `apmcmthesis.cls` 与 `refs/official_standard.json`。
2. **它是页眉判据的实测样本**：物理第 3 页印 `Page 1 of 27`（官方模板在目录后 `\setcounter{page}{1}`），`mmkit/gauntlet.py` 的页号连续性判据就是拿它和 `SHUWEI2025_A` 校准的。
3. **它有 13 份审读报告**，是评审队的真实输出样本，比空模板有用。

## 注意

`apmcmthesis.cls` 是历史遗留的模板文件名——APMCM 与数维杯早期共用同一套 cls，**这不代表它是亚太杯题目**。
