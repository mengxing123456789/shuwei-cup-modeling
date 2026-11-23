import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

# 1) protocol constants are quoted from the statement, not results -> mark them
old1 = ('Because the released protocol fixes the action space rather than our cost curve ---')
old1 = '% numerals-ok: begin\n' + old1
new1 = old1
assert t.count(old1) == 1
t = t.replace(old1, new1)

old_end = ('because waiting brings the target closer, which is the same conclusion the masking\n'
           'arms reach from the other side.')
new_end = ('because waiting brings the target closer --- the same conclusion the masking arms\n'
           'reach from the other side.\n'
           '% numerals-ok: end')
assert t.count(old_end) == 1
t = t.replace(old_end, new_end)

# 2) tighten the paragraph while keeping every measured number
old2 = ('\\slotPOfficialC{}~cm. The decomposition says why the frontier is flat in the number of\n'
        'requests: at a fixed lead a fivefold longer prefix changes the error by at most\n'
        '\\slotPPrefixGainMax{}~cm, while one second of waiting adds \\slotPDelayPenaltyMin{} to\n'
        '\\slotPDelayPenaltyMax{}~cm. A request buys lead time, not information; it helps only\n')
new2 = ('\\slotPOfficialC{}~cm. The frontier is flat in the number of requests: at a fixed lead a\n'
        'fivefold longer prefix moves the error by at most \\slotPPrefixGainMax{}~cm, while one\n'
        'second of waiting costs \\slotPDelayPenaltyMin{} to \\slotPDelayPenaltyMax{}~cm, so a\n'
        'request buys lead time rather than information. It helps only\n')
assert t.count(old2) == 1
t = t.replace(old2, new2)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('patched')