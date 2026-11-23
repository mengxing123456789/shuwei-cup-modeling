# P1-a 接入片段（供主稿直接摘用）

> 本文件只给可粘贴的正文/表/图注与 slot 建议，**不改 `main.tex`**。
> 数据源：`data/p1a_gpu_segmentation_final.json`、`data/p1a_segmentation_compare.json`。
> 图：`figures/fig9_p1a_boundary.png`（231,368 B，英文标注）。

## 1. 建议位置

P1-a 小节末尾、P1-b 之前，作为 **P1-a 的补充改进**（不要写成替代主模型）。

## 2. 正文（3 句，可直接粘贴）

```latex
To check whether the P1-a result is an artefact of clustering, we replace
Ward agglomeration and GMM-BIC model selection with an offline boundary
detector: a six-block dilated temporal CNN over the same 84-dimensional
per-frame state, trained on the 55 training records with boundary-weighted
loss and decoded by peak picking.  It raises the mean ARI on the seven
held-out records from \slotP1aARIWard{} to \slotP1aARIGpu{}
(paired difference \slotP1aARIDiff{}, 95\% CI
[\slotP1aARICILo{}, \slotP1aARICIHi{}], exact permutation
$p=\slotP1aARIP{}$, better on \slotP1aARIWins{} of seven records), while
frame-level F1 moves from \slotP1aFOneWard{} to \slotP1aFOneGpu{}
($p=\slotP1aFOneP{}$).  The gain is not free: boundaries are placed
\slotP1aBMAEDiff{}~s closer on average, but the detector over-segments, so
boundary F1 falls from \slotP1aBFOneWard{} to \slotP1aBFOneGpu{}; record~37,
a two-stage pick-and-place whose second stage is defined semantically rather
than kinematically, is the failure case (ARI \slotP1aRecThirtySeven{}).
```

数字对应：`0.4138 / 0.5487 / +0.1348 / 0.0522 / 0.2140 / 0.0469 / 6 / 0.5613 / 0.6073 / 0.4375 / 0.16 / 0.5919 / 0.1947 / 0.017`。

## 3. 表（4 行，放正文）

```latex
\begin{table}[htbp]
\centering
\caption{P1-a on the seven held-out records.  ARI and frame F1 are paired
against the Ward baseline; boundary F1 and MAE use the same $\pm5$-frame
tolerance for both methods.  The detector is trained once on 55 records and
evaluated once on the test split; no test record is used for tuning.}
\label{tab:p1a-gpu}
\begin{tabular}{lccc}
\hline
Metric & Ward + GMM-BIC & Boundary CNN & Paired difference \\
\hline
ARI & \slotP1aARIWard & \slotP1aARIGpu & \slotP1aARIDiff{} [\slotP1aARICILo, \slotP1aARICIHi] \\
Frame F1 & \slotP1aFOneWard & \slotP1aFOneGpu & \slotP1aFOneDiff \\
Boundary MAE (s) & \slotP1aBMAEWard & \slotP1aBMAEGpu & \slotP1aBMAEDiff \\
Boundary F1 & \slotP1aBFOneWard & \slotP1aBFOneGpu & \slotP1aBFOneDiff \\
\hline
\end{tabular}
\end{table}
```

## 4. 图注

```latex
\begin{figure}[htbp]
\centering
\resizebox{\slotFigWSmall}{!}{\includegraphics{figures/fig9_p1a_boundary.png}}
\caption{P1-a boundary detection on the test split.  (a) Per-frame boundary
score for record~56 (EgoStandard); orange rules mark annotated segment starts
and blue dots the 32 decoded peaks at threshold $h=0.30$.  (b) Paired ARI per
test record; the GPU detector improves six of seven records, with record~37
the exception.}
\label{fig:p1a-gpu}
\end{figure}
```

## 5. `fill_numbers.py` 建议新增 slot（来源 JSON，不手写）

| slot | JSON 路径 |
| --- | --- |
| `P1aARIWard` | `p1a_segmentation_compare.json → ari.ward_mean` |
| `P1aARIGpu` | `ari.gpu_mean` |
| `P1aARIDiff` | `ari.paired_diff` |
| `P1aARICILo/Hi` | `ari.ci95[0]` / `[1]` |
| `P1aARIP` | `ari.perm_p` |
| `P1aARIWins` | `ari.wins` |
| `P1aFOneWard/Gpu/Diff/P` | `f1.*` |
| `P1aBMAEWard` | `0.5919` 的反算源 `p1_segmentation_records.csv` 中 `method==ward` 的 `b_mae.mean()` |
| `P1aBFOneWard` | 同上，`2pr/(p+r)` 的均值 `0.5919312169` |
| `P1aBMAEGpu` / `P1aBFOneGpu` | `p1a_gpu_segmentation_final.json → test.mean_boundary_mae` / `mean_boundary_f1` |
| `P1aRecThirtySeven` | `p1a_gpu_segmentation_final_records.csv` 中 `rec==37` 的 `ari` |

## 6. 三条不能写的话

1. 不能写「全面优于 Ward」：帧 F1 不显著（p=0.4375），边界 F1 明显更差。
2. 不能写「边界检测更准」：MAE 更好，但假边界更多；要同时报 F1 与 `n_pred/n_true`。
3. 不能写「p<0.05 即强证据」：n=7，置换最小可能 p=0.0156，0.0469 只是刚过线；且早停与阈值都在同一验证集上选过。

## 7. 复跑

```powershell
cd 'E:\数学建模\_swc2026\SWC2026_C'
& 'E:\Mini\envs\mathmodel\python.exe' code\p1a_gpu_segmentation.py --seeds 3 --epochs 40
& 'E:\Mini\envs\mathmodel\python.exe' code\p1a_final_decode.py
& 'E:\Mini\envs\mathmodel\python.exe' code\p1a_compare.py
```