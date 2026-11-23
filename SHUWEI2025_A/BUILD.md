# BUILD：从空目录到可提交件

## 0. 把原件放进来（只读）

```
problem/     题面 PDF + 附件（xlsx/csv/trc/图片）。官方原件只读，要清洗就另存到 data/。
refs/        已经带了 official_standard.json 与 award_text/：baseline 要用，正文不许引用。
```

## 1. 数据层（只做一次）

```
<interp> code/fetch_*.py          # 抓数就写台账：url + fetched_at + sha256
<interp> code/features.py         # 产物进 data/*.json，不打印到屏幕
```

## 2. 建模与对账（每次改代码都要重跑）

```
<interp> code/model_a.py ... code/model_z.py
<interp> code/make_tables.py      # 表由 JSON 生成，不手抄
<interp> code/make_figures.py     # 图内 >=3 字符的字号必须 >= 6 pt
<interp> code/verify_numbers.py   # 印出来的数必须绑到 JSON 键
```

## 3. 编排

```
<interp> scripts/run_review.py metrics <本目录>    # 生成 review/00-metrics.md（口径基线）
xelatex main.tex   （两次）
<interp> scripts/gauntlet_check.py <本目录>        # R 系列
<interp> scripts/review_check.py  <本目录>         # C1..C12
```

## 4. 提交前自检（C1–C12 里可机器判的部分）

| 项 | 命令 | 期望 |
|---|---|---|
| 页码只有队号+页码 | `review_check.py` C5 | 每页都有，且不含身份信息 |
| 正文无中文（附录不算） | C7 | `body cjk=0` |
| 正文 <= 30 页 | `gauntlet_check.py` R-V01 | `body<=30` |
| 附录列全源码 | C9 + `code/*.py` 实数 | listing 数 >= 脚本数 |
| 队号两层 | C11 | 字形 0 命中 **且** 语义 0 命中 |
| 文件名 | 手工 | `A<队号>.pdf` |
| 摘要页第 1、目录第 2 | C4 | 两页都对 |
| 参考文献类型标记 | C8 | `[M]/[J]/...` 数 >= 条目数 |
