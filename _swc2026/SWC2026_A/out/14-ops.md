# 流水线运维记录（A 题）

VERDICT: PASS

## 1. 环境事实

| 项 | 值 |
|---|---|
| 解释器 | `E:\Mini\envs\mathmodel\python.exe`（Python 3.11.18） |
| 关键依赖 | numpy 2.4.6、pandas、scipy、matplotlib、openpyxl、pyarrow 26.0.1、pymupdf |
| LaTeX | `E:\MIKTEX\miktex\miktex\bin\x64\pdflatex.exe`（MiKTeX，TeX Live 兼容） |
| 操作系统 | Windows 11，单机 16 GB 内存 |

## 2. 已知环境坑与处置

1. **`numpy.libs` 缺失导致 `0xC06D007F`**：随包 OpenBLAS DLL 目录丢失，`np.dot` / `np.linalg.*` / `np.corrcoef` / `np.polyfit` 全部原生崩溃，且无 Python 栈。处置：`pip install --force-reinstall --no-cache-dir numpy==2.4.6`，并在 `run_all.py` 启动时做 `np.linalg.inv` 自检。
2. **MiKTeX 首次编译报 `security risk: running with elevated privileges`**：属警告，第二次编译即通过；不影响 PDF。
3. **PowerShell 读取 UTF-8 中文**：`Get-Content` 默认按 ANSI 解码，必须加 `-Encoding UTF8` 或用 `[System.IO.File]::ReadAllText(..., UTF8)`。
4. **`numpy.corrcoef` 与 `numpy.polyfit` 旧坑**：已由 numpy 重装修复，但 `verify_numbers.py` 仍用自写 OLS，避免依赖 BLAS。

## 3. 一条命令复现

```powershell
$PY = 'E:\Mini\envs\mathmodel\python.exe'
$DIR = 'E:\数学建模\_swc2026\SWC2026_A'
Set-Location $DIR
& $PY code\run_all.py          # 116.4 s，全部 data/*.json 与 tables/figures 重生成
$env:PATH = 'E:\MIKTEX\miktex\miktex\bin\x64;' + $env:PATH
& pdflatex -interaction=nonstopmode -halt-on-error main.tex
& pdflatex -interaction=nonstopmode -halt-on-error main.tex
& $PY code\verify_numbers.py   # 116 claims, failures=0
& $PY 'E:\数学建模\.agents\skills\mathmodeling\scripts\gauntlet_check.py' $DIR   # 16/16 PASS
```

## 4. 本轮运行记录

| 步骤 | 命令 | 耗时 | 结果 |
|---|---|---|---|
| 求解 | `code/run_all.py` | 116.4 s | 7 JSON + 12 表 + 8 图 |
| 数值核验 | `code/verify_numbers.py` | 0.4 s | 116 claims / 0 failures |
| 编译 | `pdflatex ×2` | 22 s / 18 s | 24 页，0 overfull，0 undefined |
| 格式体检 | `gauntlet_check.py` | 5.0 s | 16/16 PASS |
| 字体测量 | `mmkit.figfont` | 0.3 s | min 5.98 pt，violations 0 |

## 5. 失败模式与回滚

- **任何脚本非零退出**：`run_all.py` 立即停止，不覆盖已有 JSON；旧 JSON 保持上一次成功状态。
- **PDF 编译失败**：保留 `main.log`，从 `main.tex` 的上一版恢复（本目录无 git，但 `_legacy_zh_figures/` 保留了旧图）。
- **数值核验失败**：`verify_numbers.py` 打印 `FAIL <key>` 行并以非零退出；先查对应 JSON 键，再改模型，不改断言。
- **时间预算**：全流程 <3 分钟（不含人工写作），可在 8 GB 内存机器上运行。

## 6. 目录与清理

- 临时文件：`main.aux`、`main.log`、`main.out`、`main.toc` 均为编译副产物，可删。
- 旧中文图：已移至 `_legacy_zh_figures/`，不参与论文；正式图为 `figures/fig_*.pdf`（8 组，英文）。
- 冻结产物：`data/*.json` 的 `_meta` 记录脚本名、生成时间与输入 sha256；论文中的每个数字都能回到对应键。
