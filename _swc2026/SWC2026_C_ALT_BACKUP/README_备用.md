# 备用稿：数维杯 2026 C 题（第二思路）

- **性质**：备用。与 `..\SWC2026_C` 的正式稿**完全独立**，从零起草，方法与结论均不同。
- **原稿思路**（对照用，不复制）：32 维手工状态向量 + Ward 聚类 + 监督式可靠性分类器；ridge 回归 + 共形预测 + 固定阈值再观测；SLACK/EDF 启发式调度。
- **本稿思路**：贝叶斯在线变点检测（BOCPD）+ 分层 Beta-Binomial 可靠性；三维常速度卡尔曼滤波 + 价值-of-information 观测调度；场景化机会约束混合整数规划（CC-MIP）+ 滚动时域重规划。
- **写作语言**：英文（数维杯规则）；页数目标：正文 ≤ 25 页（含摘要与目录），附录不限。
- **队号**：SWBMCM2634892；选题：C。
- **数据**：`<RESTOCK_DATA_ROOT>`（原始包只读）。
- **建立时间**：2026-11-21。

## 目录

```
code/        本稿的全部计算脚本（每个数字都可复跑）
data/        本稿脚本产出的 JSON
figures/     本稿图件
out/         各步的法定产物（BYTES / VERDICT 协议）
tables/      自动生成的 LaTeX 表
review/      评审产物
main.tex     论文源文件
main.pdf     编译产物
```

## 复跑

```powershell
$PY='E:\Mini\envs\mathmodel\python.exe'
& $PY code\alt_p1_bocpd.py
& $PY code\alt_p2_kalman.py
& $PY code\alt_p3_ccmip.py
& $PY code\alt_make_figures.py
xelatex main.tex; xelatex main.tex
```
