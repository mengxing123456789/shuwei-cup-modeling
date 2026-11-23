import pathlib
p = pathlib.Path(r'48-官网通知逐条核对与AIGC风险.md')
s = p.read_text(encoding='utf-8')
reps = [
("**AI 工具使用规定：程序化条款（声明、报告、脚本注释、正文标注）现已全部满足，190/190 脚本带注释。**",
 "**AI 工具使用规定：程序化条款（声明、报告、脚本注释、正文标注）现已全部满足，196/196 个随包脚本带版本化注释。**"),
("| 承诺书命名 | `题号+队伍编号+cns`，pdf/jpg/png，须电子签名或手写签名后扫描 | `CSWBMCM2634892cns.pdf` 17,080 B，**仅 1. Shuping Zhang，无签名** | ⚠️ 待你本人签名 |",
 "| 承诺书命名 | `题号+队伍编号+cns`，pdf/jpg/png，须电子签名或手写签名后扫描 | `CSWBMCM2634892cns.pdf` **198,274 B，已含手写签名（Shuping Zhang，2026-11-23）** | ✅ |"),
("| 体积 | 论文及全部附件建议 ≤20 MB | 1.87 + 0.017 + 11.9 = **13.8 MB** | ✅ |",
 "| 体积 | 论文及全部附件建议 ≤20 MB | 2.36 + 0.19 + 12.11 = **14.66 MB** | ✅ |"),
("| **正文 ≤25 页（含摘要页、目录页），附录不限** | `page_report`：body **25** / appendix 44 / total 69 | ✅ 顶格但合规 |",
 "| **正文 ≤25 页（含摘要页、目录页），附录不限** | `page_report`：body **25** / appendix **42** / total **67** | ✅ 顶格但合规 |"),
("| 正文每页页眉队伍编号+页码 | p2–p25：`Team CSWBMCM2634892` / `Page n of 25`；p26 起 `Appendix, p. n` | ✅ |",
 "| 正文每页页眉队伍编号+页码 | p3–p25：`Team CSWBMCM2634892` / `Page n of 25`；p1/p2 按官方 demo 不编号；p26 起 `Appendix, p. n` | ✅ |"),
("| ⑤ 正文相应位置标注 + 参考文献列工具 | 格式 `[编号] 工具名称，版本/型号，开发机构/公司，使用日期` | `\\bibitem{deepseek} DeepSeek Harness, CLI coding agent [EB/OL], DeepSeek, 18--20 Nov 2026.` | ✅ |",
 "| ⑤ 正文相应位置标注 + 参考文献列工具 | 格式 `[编号] 工具名称，版本/型号，开发机构/公司，使用日期` | `\\bibitem{deepseek} DeepSeek Harness, version 0.2.2-rc.3, CLI coding agent [EB/OL], DeepSeek, 18--22 Nov 2026.` | ✅ |"),
("| ⑥ 附《AI 工具使用情况报告》，不计页数 | 逐工具填 7 项 | 表 `tab:aitools` 覆盖 Tool/Dates/Stages/Key prompts/Outputs adopted/Outputs rejected/Team revision，**7/7 齐全** | ✅ |",
 "| ⑥ 附《AI 工具使用情况报告》，不计页数 | 逐工具填 7 项 | 表 `tab:aitools` 覆盖 Tool（含版本/机构/发布日期）、Dates、Use、Key prompts、Outputs adopted、Outputs rejected、Human revision、Team check，**齐全** | ✅ |"),
("| ⑦ **脚本注释须标明 AI 辅助** | 工具名、版本/型号、机构、发布日期 | 本轮前 98/190；**本轮已补 92 个，现 190/190** | ✅ 已修 |",
 "| ⑦ **脚本注释须标明 AI 辅助** | 工具名、版本/型号、机构、发布日期 | **196/196 个随包脚本均为 `DeepSeek Harness 0.2.2-rc.3, released by DeepSeek (November 2026)`** | ✅ |"),
("| ① 允许用途边界 | 可用于检索/归纳/润色/翻译/代码语法/常规绘图/数据预处理；**模型构建、算法设计与求解、推导、结果解读须队员独立完成** | 论文 `tab:pass` 记录了团队先定的判据与门槛；`§7` 写明哪些是团队决策 | ✅ 已声明 |",
 "| ① 允许用途边界 | 可用于检索/归纳/润色/翻译/代码语法/常规绘图/数据预处理；**模型构建、算法设计与求解、推导、结果解读须队员独立完成** | Appendix B 明写 AI 仅用于脚本起草/调试与重复性文本变换；模型、推导、结果解读为团队完成 | ✅ 已声明 |"),
("| ② 须自行改写，禁止照搬 | 论文文字与结论须队伍自行改写 | Appendix 报告写明「drafted scripts and prose」，并列出团队复核方式 | ⚠️ 见第 5 节 |",
 "| ② 须自行改写，禁止照搬 | 论文文字与结论须队伍自行改写 | Appendix B 写明「AI prose was not copied into the paper」，并列出团队复核方式 | ✅ |"),
("| ③ 须声明 | 正文结尾或参考文献后声明 | `\\subsection*{AI tool usage report}` 在附录 C | ✅ |",
 "| ③ 须声明 | 正文结尾或参考文献后声明 | `\\subsection*{AI tool usage report}` 在 Appendix B（参考文献后） | ✅ |"),
("| ④ 事实/公式须可核 | 虚构或查不到来源一律删除；**缺完整推导的公式评审可不认可** | 143 条断言 + 136 条数值不变量 + 附录 I 两条命题带证明 | ✅ |",
 "| ④ 事实/公式须可核 | 虚构或查不到来源一律删除；**缺完整推导的公式评审可不认可** | 145 条断言 + 136 条数值不变量 + 附录 I 两条命题带证明 | ✅ |"),
("## 6. 还需要你本人做的三件事\n\n1. **承诺书签名**：`CSWBMCM2634892cns.pdf` 现只有 `1. Shuping Zhang` 打印名，无手写/电子签名。官网要求「电子签名，或打印后手写签名，再拍照、扫描」。\n2. **提交**：登录 `https://www.mojinghub.com/competitions/swbmcm/2026` → 个人中心 → 我的竞赛 → 报名管理 → 参赛入口，三项分别上传，**必须点「点击提交」看到「已提交」**。建议 11-23 就交一次，留出重交窗口。\n3. **（可选）真实 AIGC 自测**：若学校有知网/维普 AIGC 检测额度，交前跑一次拿真实百分比。",
 "## 6. 还需要你本人做的两件事\n\n1. **提交**：登录 `https://www.mojinghub.com/competitions/swbmcm/2026` → 个人中心 → 我的竞赛 → 报名管理 → 参赛入口，三项分别上传，**必须点「点击提交」看到「已提交」**。建议 11-23 就交一次，留出重交窗口。\n2. **（可选）真实 AIGC 自测**：若学校有知网/维普 AIGC 检测额度，交前跑一次拿真实百分比。"),
("| `code/*.py`（92 个） | 顶部插入组委会第 ⑦ 条要求的生成式工具注释（工具名/版本/机构/日期） |",
 "| `code/*.py`（196 个随包脚本） | 顶部统一为组委会第 ⑦ 条要求的生成式工具注释（工具名/版本/机构/发布日期） |"),
]
for a,b in reps:
    c=s.count(a)
    if c==0: print('MISS:', a[:60])
    s=s.replace(a,b,1)
p.write_text(s, encoding='utf-8', newline='\n')
print('done')
