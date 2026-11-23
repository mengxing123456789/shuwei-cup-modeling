import pathlib
p = pathlib.Path(r"code\make_appendix_l.py")
t = p.read_text(encoding="utf-8")
pairs = [
('rows.append(r"ladder. A blind equal-thirds split already reaches ARI \\slotPZeroThirdARI{}, and a")',
 'rows.append(rf"ladder. A blind equal-thirds split already reaches ARI {zero[\'thirds\'][\'mean_ari\']:.4f}, and a")'),
('rows.append(r"blind midpoint split reaches \\slotPZeroMidARI{}. The learned detector must be read")',
 'rows.append(rf"blind midpoint split reaches {zero[\'midpoint\'][\'mean_ari\']:.4f}. The learned detector must be read")'),
('rows.append(r"\\slotPOfficialInvalid{} invalid actions, a valid-protocol flag of")',
 'rows.append(rf"{au[\'invalid_actions\']} invalid actions, a valid-protocol flag of")'),
('rows.append(r"\\slotPOfficialValid{}, budget compliance \\slotPOfficialBudget{} and horizon")',
 'rows.append(rf"{str(au[\'valid_protocol\']).lower()}, budget compliance {au[\'budget_ok_rate\']*100:.0f}\\\\% and horizon")'),
('rows.append(r"compliance \\slotPOfficialHorizon{}. The corrected-protocol reference values for")',
 'rows.append(rf"compliance {au[\'horizon_ok_rate\']*100:.0f}\\\\%. The corrected-protocol reference values for")'),
('rows.append(r"corrected protocol gives weighted completion \\slotPStochCompSTwo{}/\\slotPStochCompSThree{}")',
 'rows.append(r"corrected protocol gives weighted completion \\slotPStochSTwoSlackOldComp{}/\\slotPStochSThreeSlackOldComp{}")'),
('rows.append(r"and weighted on-time \\slotPStochOnTimeSTwo{}/\\slotPStochOnTimeSThree{} in S2/S3. These")',
 'rows.append(r"and weighted on-time \\slotPStochSTwoSlackOldETA{}/\\slotPStochSThreeSlackOldETA{} in S2/S3. These")'),
]
for a, b in pairs:
    if a not in t:
        raise SystemExit("MISS: " + a[:60])
    t = t.replace(a, b)
p.write_text(t, encoding="utf-8")
print("patched")
