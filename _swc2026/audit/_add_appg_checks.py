from pathlib import Path

p = Path(r"E:\数学建模\_swc2026\audit\verify_claims.py")
t = p.read_text(encoding="utf-8")

anchor = '    out = AUD / "verify_claims.json"'
assert t.count(anchor) == 1

block = r'''    # --- Appendix G: second-round experiments ------------------------------
    import hashlib as _hl
    _gpath = C / "tables" / "app_g.tex"
    _g = _gpath.read_text(encoding="utf-8") if _gpath.exists() else ""
    _man = load_json("app_g_manifest.json") if (C / "data" / "app_g_manifest.json").exists() else {}
    check("Appendix G 表文件存在且含四张表",
          all(k in _g for k in ("tab:gpu-ledger", "tab:p1b-arms", "tab:p2quant", "tab:p3engine")),
          f"bytes={len(_g)}", True, len(_g) > 0)
    check("Appendix G 文件哈希与生成清单一致（可由 JSON 重新生成）",
          bool(_man) and _hl.sha256(_g.encode("utf-8")).hexdigest() == _man.get("sha256"),
          f"manifest={_man.get('sha256','--')[:16]}", "match", _man.get("sha256", "--")[:16])
    _p1b2 = load_json("up_p1b_dual.json")
    _a = _p1b2["arms"]["A_baseline_replica"]["test_ap"]
    _c = _p1b2["arms"]["C_dual_plus_multitask"]["test_ap"]
    _lift = f"{100.0 * (_c / _a - 1.0):.1f} per cent"
    check("Appendix G 正文的 AP 相对增益与 JSON 一致", _lift in _g, _lift, _lift, _lift)
    _rev = load_json("up_p3_review.json")
    _bd = f"{_rev['verdict']['best_delta_pt']:.3f}"
    check("Appendix G 复核臂最好格与 JSON 一致", _bd in _g, _bd, _bd, _bd)
    check("正文在 Appendix D 之外还引用了 Appendix G",
          "Appendices~D and~G" in main_text, "main.tex", True, "Appendices~D and~G" in main_text)

'''

t = t.replace(anchor, block + anchor)
p.write_text(t, encoding="utf-8", newline="\n")
print("patched verify_claims with Appendix G checks")
