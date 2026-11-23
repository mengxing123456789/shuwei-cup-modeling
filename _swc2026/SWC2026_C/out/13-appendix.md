BYTES 2218
# 13 附录与自指：清单与可复算核对（SWC2026 C）

## 1 附录结构

| 节 | 内容 | 载体 | 字节 |
|---|---|---|---|
| A Notation | 符号表 | `tables/app_g.tex` | 8,600 |
| B Key code | 5 个核心片段 | `\lstinputlisting`（见 §2） | — |
| C Reproduction commands | 复现命令 | `tables/app_h.tex` | 6,871 |
| D Closed-form calibration | 闭式校准推导 | `tables/app_i.tex` | 5,882 |
| E Annotation audit | 标注审计与未见任务类 | `tables/app_j.tex` | 4,102 |
| F The chain in one picture | 论证链总图 | `tables/app_k.tex` | 5,219 |
| G Second-round experiments | 第二轮实验 | `tables/app_l.tex` | 15,825 |

## 2 源码清单（`\lstinputlisting`，实测存在）

| 文件 | 字节 | SHA-256 前 12 |
|---|---|---|
| `snippets/p1_state_hand_feats.py` | 2,025 | `d545e8018777` |
| `snippets/p1_model_ward_segments.py` | 830 | `78beccea10a5` |
| `snippets/p2_predict_windows.py` | 945 | `be4234973d77` |
| `snippets/p3_schedule_p_late.py` | 340 | `5618fc070cbe` |
| `snippets/reproduce.ps1` | 3,214 | `bbf777875907` |

全部 5 个目标文件存在且非空；编译时由 `\lstinputlisting` **从磁盘现读**，因此正文里印出的代码永远与文件一致，不存在“印的是旧版”的风险。

## 3 自指检查（关键）

- **本稿没有 `figures/code_index.tex`**：源码索引不是“脚本 → 字节数”的表格，而是直接 `\lstinputlisting` 内联，故不存在“印出来的字节数与磁盘不符”的自指风险（`gate_g17` 对此返回 NA 而不是 FAIL）。
- 全文检索 `\bbytes?\b` 只有 1 处，是正文在讲 CSV 的 UTF-8 BOM（第 255 行附近），不是自指计数。
- 附录里没有任何“某文件 N 字节”“共 N 条”的硬编码数字；所有计数型陈述由表内数据本身承载。

## 4 复算命令

```powershell
# 5 个 listing 是否存在、字节数是否与本表一致
Get-ChildItem E:\数学建模\_swc2026\SWC2026_C\snippets\*.py, E:\数学建模\_swc2026\SWC2026_C\snippets\*.ps1 | Select Name,Length
# 附录表是否都被 main.tex 引入
Select-String -Path E:\数学建模\_swc2026\SWC2026_C\main.tex -Pattern 'tables/app_[g-l]\.tex'
```

VERDICT: PASS
