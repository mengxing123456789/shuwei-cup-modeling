# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import io
import json

p = r"data/up2_p1a.json"
d = json.load(io.open(p, encoding="utf-8"))
cfg = d["configs"]
bv = max(cfg, key=lambda c: c["val_ari"] + 0.5 * c["val_bf1"])
bt = max(cfg, key=lambda c: c["test_ari"])
bb = max(cfg, key=lambda c: c["test_bf1"])
d["best_by_test"] = dict(name=bt["name"], test_ari=bt["test_ari"], test_bf1=bt["test_bf1"])
d["best_bf1_on_test"] = dict(name=bb["name"], test_ari=bb["test_ari"], test_bf1=bb["test_bf1"])
d["notes"] = (
    "选型只用验证集（obj = val ARI + 0.5*val bf1 的网格 argmax；K 先验惩罚扫过但会拉低验证 ARI，"
    "因此 k_pen=0），test 只评一次。baseline 是已发表口径的对照（test ARI 0.5806 / bf1 0.1200）。"
    "验证集最优的 C2 在 test 上退化（bf1 0.132->0.031，过分割：平均 npred 18.1 vs 真实 K 均值 8.3），"
    "说明多任务头的验证优势没有跨环境迁移；test 上最好的是 C1（只用新解码器重放 v1 分数）与 C3。"
    "预注册门槛 test ARI>=0.62 且 bf1>=0.30 未达到，passes=false。"
    "最弱记录始终是 rec37（真值 K=2，所有配置都给出 11-14 段，ARI~0.02），单条记录把均值拉低约 0.08。"
)
json.dump(d, io.open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print("annotated", d["best_by_test"], d["best_bf1_on_test"])