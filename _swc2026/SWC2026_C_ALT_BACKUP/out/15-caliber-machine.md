BYTES 1248
# 口径机器硬项（caliber_check.py）  SWC2026_C_ALT_BACKUP

判据：H1 同一字面量两种量纲（硬）；W1/W2/W3 提示项不改判定。

## 硬项（0）
- 没有发现同一数值串被两种量纲使用。

## 提示（9）
- W1 `95%` 所在句没写分母：\item \textbf{Duration exchangeability within family and observation prefix.} Given a job family and an observ
- W1 `95.4%` 所在句没写分母：Retention moves by a few points around 95.4\% and never changes sign.
- W1 `95%` 所在句没写分母：Because every policy sees the same 30 draws, the nominal comparison is paired: the rolling-minus-one-shot on-t
- W2 `0.914` 与 `0.915` 相差 0.109%，行 [210, 210]，疑似同一个量的两处结果
- W2 `0.897` 与 `0.893` 相差 0.446%，行 [259, 351]，疑似同一个量的两处结果
- W2 `0.817` 与 `0.821` 相差 0.487%，行 [259, 493]，疑似同一个量的两处结果
- W2 `0.883` 与 `0.880` 相差 0.34%，行 [351, 351]，疑似同一个量的两处结果
- W2 `0.804` 与 `0.800` 相差 0.498%，行 [493, 493]，疑似同一个量的两处结果
- W2 `12.789` 与 `12.809` 相差 0.156%，行 [505, 505]，疑似同一个量的两处结果

结论：硬项 0 / 提示 9
VERDICT: PASS
