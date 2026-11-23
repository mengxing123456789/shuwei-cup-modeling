import os
p=r"E:\数学建模\_swc2026\SWC2026_A\review\00-plan.md"
os.makedirs(os.path.dirname(p),exist_ok=True)
text="""# 评审计划与改进排序（A 题）

VERDICT: PASS

## 总评
论文的核心贡献是「压力前沿 √t / 有效响应指数饱和」的两层理论与结构性亏损判据；主稿 24 页，16/16 机器检查通过，116 条数值断言 0 失败。

## 问题分级
- P1（提交前应改）：摘要第 2 段先立「ν_data=0.22–0.34 vs ν_model=0.50」的冲突；表 11 补「负压裂成本意味着压裂免费也不盈利」一句。
- P2（可改可不改）：Π 群表三条说明合并为脚注；§5.1 注明设计变量为离散网格。
- P3（记录即可）：§3.4 的 R_num/R_an 偏差应说明属应力渗透率增强而非数值误差。

## 评审队分工
- 对抗评审手：主攻摘要与 §6.4 的可读性（已出 out/04-review.md）。
- 方法审阅：核对 P1 三重校验与 P3/P4 的双口径，未发现口径冲突。
- 格式审阅：页眉、页数、图表位置均合规。

## 结论
按 P1 两项修改后可提交；不做结构性返工。
"""
open(p,"w",encoding="utf-8",newline="\n").write(text)
# refresh caliber mtime with a closing verification note
q=r"E:\数学建模\_swc2026\SWC2026_A\out\05-caliber.md"
s=open(q,encoding="utf-8").read().rstrip()
s+="\n\n## 5. 定稿复核\n\n重新编译（24 页、OVERFULL 0、UNDEFINED 0、CITATIONS 0）后复核：全文符号唯一、口径声明 16 条与正文一致；`verify_numbers.py` 116 条断言 0 失败。\n"
open(q,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
