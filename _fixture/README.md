# `_fixture` — 流水线冒烟测试夹具

一个**故意做到最小**的假论文目录，用来验证 `pipeline.py` 的门禁逻辑本身没坏，而不需要跑真的建模。

## 文件

| 文件 | 内容 |
| --- | --- |
| `main.tex` | 11 行的最小论文，含一个 `\section`、一个数字、一条引用 |
| `main.pdf` | 编译产物（17 KB，1 页） |
| `code/verify_numbers.py` | 最小断言脚本：检查 `data/results.json` 里的数是否等于正文里的数 |
| `data/results.json` | `{"answer": 42}` |
| `logs/fixture.log` | 上次冒烟运行的输出 |
| `main.aux` / `main.log` / `main.out` | 编译中间产物 |

## 怎么用

```powershell
$PY = "python"   # 或设 MM_PY 指向你的解释器
& $PY .agents\skills\mathmodeling\scripts\pipeline.py _fixture --status
& $PY .agents\skills\mathmodeling\scripts\gauntlet_check.py _fixture
```

预期：`pipeline --status` 显示八步里大部分是 NA（这个夹具没有 `out/` 产物），`gauntlet_check` 报 16 项里的结构项通过、内容项 NA。**如果这里报的不是 NA 而是 FAIL，说明门禁代码有 bug，不是夹具的问题。**

## 为什么值得占 8 个文件

改 `pipeline.py` / `gauntlet.py` / `verify_numbers.py` 的判据时，跑真论文要几分钟，跑夹具要几秒。单元测试（`scripts/tests/`，70 条）覆盖的是函数级逻辑，夹具覆盖的是**端到端**：真的建目录、真的编译、真的读 PDF 页数。

## 与 `PRACTICE_2023B` 的区别

`PRACTICE_2023B` 是真做过的 2023 年 B 题（棉秆热解），用于验证流水线在**真实规模**下能跑通；`_fixture` 是假数据，用于验证**判据本身**。前者慢、后者快，两者不能互相替代。
