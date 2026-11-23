# `.mh` — 索引缓存

流水线自己维护的索引，不是手写文档。

| 文件 | 内容 | 怎么重建 |
| --- | --- | --- |
| `corpus.json` | 229 条语料记录（题面 / 获奖论文 / 附件 / 数据），每条含 `year`、`problem`、`kind`、`file`、`pages`、`chars`、`title`、`head`（首页正文前 600 字） | `python .agents/skills/mathmodeling/scripts/corpus_index.py --build` |
| `vision_ledger.json` | 图表视觉审查的已判记录（哪张图、判了什么、谁判的） | 由 `scripts/vision_review.py` 追加 |

## 为什么 `file` 存的是相对路径

`corpus.json` 里的 `file` 字段是**相对 `corpus/` 的路径**，不是绝对路径。这样仓库换机器、换盘符都不失效。

`mmkit/corpus.py` 的 `_rebase()` 在 `load()` 时把相对路径拼回当前 `corpus_root()`：

```python
from mmkit import corpus as C
idx = C.load()
rec = idx["records"][0]
full = C.corpus_root() / rec["file"]     # 拿到真实路径
```

如果索引是在别的盘下建的（`file` 里带 `E:\...`），`_rebase()` 会找路径里的 `corpus` 段、取其后缀，只要仓库结构一致就能对上。实测在 `E:\_clonetest2` 克隆里 229 条记录全部解析成功，0 条仍是绝对路径，0 条文件缺失。

## 重建代价

`corpus_index.py --build` 要读 124 篇 PDF 的首页 + 720 份真题，约 2–4 分钟。索引不进 `.gitignore`（351 KB，比重建便宜）。

<!-- path-note -->
