import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

mark_start = 'Because the released protocol fixes the action space rather than our cost curve'
assert t.count(mark_start) == 1, t.count(mark_start)
t = t.replace(mark_start, '% numerals-ok: begin\n' + mark_start)

old_end = ('because waiting brings the target closer, which is the same conclusion the masking\n'
           'arms reach from the other side.')
new_end = ('because waiting brings the target closer --- the same conclusion the masking arms\n'
           'reach from the other side.\n'
           '% numerals-ok: end')
assert t.count(old_end) == 1, t.count(old_end)
t = t.replace(old_end, new_end)

old2 = ('\\slotPOfficialC{}~cm. The decomposition says why the frontier is flat in the number of\n'
        'requests: at a fixed lead a fivefold longer prefix changes the error by at most\n'
        '\\slotPPrefixGainMax{}~cm, while one second of waiting adds \\slotPDelayPenaltyMin{} to\n'
        '\\slotPDelayPenaltyMax{}~cm. A request buys lead time, not information; it helps only\n')
new2 = ('\\slotPOfficialC{}~cm. The frontier is flat in the number of requests: at a fixed lead a\n'
        'fivefold longer prefix moves the error by at most \\slotPPrefixGainMax{}~cm, while one\n'
        'second of waiting costs \\slotPDelayPenaltyMin{} to \\slotPDelayPenaltyMax{}~cm, so a\n'
        'request buys lead time rather than information. It helps only\n')
assert t.count(old2) == 1, t.count(old2)
t = t.replace(old2, new2)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('patched')