import io

# 1) slots
fp = r'E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py'
s = io.open(fp, encoding='utf-8').read()
anchor = 'add("PSegGPUValBFOne"'
i = s.find(anchor)
assert i > 0, 'anchor for slot insertion not found'
block = (
    'add("POfficialA", "p2_official", ["options", 0, "rmse_cm"], "f2")\n'
    'add("POfficialB", "p2_official", ["options", 1, "rmse_cm"], "f2")\n'
    'add("POfficialC", "p2_official", ["options", 2, "rmse_cm"], "f2")\n'
    'add("PDelayPenaltyMin", "p2_official", ["derived", "delay_penalty_cm_by_ctx", "@min"], "f2")\n'
    'add("PDelayPenaltyMax", "p2_official", ["derived", "delay_penalty_cm_by_ctx", "@max"], "f2")\n'
    'add("PPrefixGainMax", "p2_official", ["derived", "prefix_gain_cm_by_lead", "@max"], "f2")\n'
)
s = s[:i] + block + s[i:]
io.open(fp, 'w', encoding='utf-8', newline='\n').write(s)
print('slots inserted')

# 2) prose
p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()
old = ('The return delay is a protocol constant, \\slotPSchedDelayDistribution{}~s\n'
       '(`observation.delay\\_s`); the package ships no measurement of it, so every\n'
       're-observation we price below assumes that value and we report the assumption rather\n'
       'than a distribution.')
old = old.replace('(`', '(\\texttt{').replace('\\_s`)', '\\_s})')
new = ('The return delay is a protocol constant, \\slotPSchedDelayDistribution{}~s\n'
       '(\\texttt{observation.delay\\_s}); the package ships no measurement of it, so we\n'
       'report the assumption rather than a distribution.\n'
       '\n'
       'Because the released protocol fixes the action space rather than our cost curve ---\n'
       'prefixes of 0.2, 0.6 and 1.0~s, a one-second delay, a unit cost and at most two\n'
       'requests --- we also solve the decision inside that space, at a three-second deadline.\n'
       'One request then leaves two seconds of lead and two requests one, and the error of the\n'
       'same frozen predictor at the three options is \\slotPOfficialA{}, \\slotPOfficialB{} and\n'
       '\\slotPOfficialC{}~cm. The decomposition says why the frontier is flat in the number of\n'
       'requests: at a fixed lead a fivefold longer prefix changes the error by at most\n'
       '\\slotPPrefixGainMax{}~cm, while one second of waiting adds \\slotPDelayPenaltyMin{} to\n'
       '\\slotPDelayPenaltyMax{}~cm. A request buys lead time, not information; it helps only\n'
       'because waiting brings the target closer, which is the same conclusion the masking\n'
       'arms reach from the other side.')
assert t.count(old) == 1, ('anchor count', t.count(old))
t = t.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('prose replaced')