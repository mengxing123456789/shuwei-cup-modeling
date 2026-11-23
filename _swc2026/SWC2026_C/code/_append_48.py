import pathlib
p = pathlib.Path(r'48-官网通知逐条核对与AIGC风险.md')
s = p.read_text(encoding='utf-8')
s = s.replace('核对时间：2026-11-22 13:5x　核对人：本轮会话',
              '核对时间：2026-11-22 21:15（终检）　核对人：本轮会话', 1)
s += """

---

## 8. 终检结论（2026-11-22 21:15 更新）

### 8.1 已合规（无需你再改）

| 项 | 终态 |
|---|---|
| 正文页数 | 25 页（含摘要页、目录页）；附录 42 页；总 67 页 |
| 页眉 | p1/p2 按官方 demo 不编号；p3–p25 为 `Team CSWBMCM2634892` + `Page 3 of 25` … `Page 25 of 25`；p26 起 `Appendix, p. 26`… |
| 字体/纸张 | `Swmcmthesis` 内部 `a4paper,12pt`；字体 TeXGyreTermesX（Times 度量克隆，与官方 demo 同款） |
| 第一页/第二页 | p1 题目+Summary+Key word；p2 仅 Contents |
| 身份匿名 | 论文正文/附录 `Nanchang`/`University`/`Shuping`/电话/邮箱 0；CJK 0 |
| 参考文献 | 9 条，按正文引用次序；[4][5][6] 已补 `pp. 1–462`/`pp. 1–324`/`pp. 1–897`；[9] 已补版本、机构、日期、URL、访问日期 |
| 源程序 | 随包 196 个 `.py`；`snippets/reproduce.ps1` 可移植并支持 `-Full`；`requirements.txt`；`data/derived_manifest.json`（165 个派生 JSON 的 sha256） |
| AI 声明 | Appendix B 报告已含 Tool 版本/机构/发布日期、Use、Key prompts、Outputs adopted/rejected、Human revision、Team check；并声明「Every figure and table … covered by this declaration」；正文已写 AI 仅做脚本与重复性工作 |
| 承诺书 | `CSWBMCM2634892cns.pdf` 198,274 B，已含 Shuping Zhang 手写签名、日期 2026-11-23 |
| 体积 | 论文 2,475,359 B + 承诺书 198,274 B + 支撑包 12,700,761 B = 14.66 MB，低于 20 MB |

### 8.2 待你抉择（不影响提交，但可再提升）

1. **支撑材料里的本地绝对路径**：`CSWBMCM2634892fj.zip` 中 18 个文件含 `C:\\Users\\29900` 或 `.`。这些是脚本/数据清单里的路径，不影响论文匿名条款，但打开支撑包会看到本机用户名。要清理需要改 18 个文件并重算 `derived_manifest.json` 的 sha256，约 10–15 分钟。**建议：清理**。
2. **AIGC 真实百分比**：本地只能给文风代理指标，不能给组委会那套检测器的数值。若学校有知网/维普 AIGC 额度，提交前测一次；没有就按当前文风指纹（13 项均在人类获奖稿区间内）提交。**建议：能测则测，不能测直接交**。
3. **提交渠道**：官网 vs 备用邮箱二选一；官网需看到「已提交」。**建议：11-23 先交一次，留重交窗口**。

### 8.3 一句话

**格式与 AI 程序化条款已全部满足；剩下只有「支撑包绝对路径清理」和「AIGC 真实自测」两件可选事项，以及你本人去点提交。**
"""
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
