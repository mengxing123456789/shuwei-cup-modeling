from pathlib import Path

p = Path(r"code\make_appendix_g.py")
t = p.read_text(encoding="utf-8")

t = t.replace(
    'r"GPU seconds are wall-clock on one RTX~4060 Laptop (8\\,GB); CPU-only rows are marked.}")',
    'r"GPU seconds are wall-clock on one RTX~4060 Laptop (8\\,GB).}")',
)

t = t.replace(
    '            w = a.get("worst_env", worst.get(key))',
    '            _pe = a.get("per_env") or []\n'
    '            w = min((x["auc_bad"] for x in _pe), default=worst.get(key))',
)

t = t.replace(
    "f\"{p2['_meta']['epochs']} & 3 & {f(p2['_meta']['gpu_train_seconds'],1)} & \"",
    "f\"{p2['_meta']['epochs']} & 3 & {f(sum(p2['_meta']['gpu_train_seconds_by_seed'].values()),1)} & \"",
)

t = t.replace(
    '        total_gpu += p2["_meta"]["gpu_train_seconds"]',
    '        total_gpu += sum(p2["_meta"]["gpu_train_seconds_by_seed"].values())',
)

t = t.replace(
    "f\"{f(p1b['arms']['C_dual_plus_multitask'].get('worst_env', p1b['_meta']['baseline']['worst_env']),4)}. \"",
    "f\"{f(min(x['auc_bad'] for x in p1b['arms']['C_dual_plus_multitask']['per_env']),4)}. \"",
)

p.write_text(t, encoding="utf-8", newline="\n")
print("patched")
