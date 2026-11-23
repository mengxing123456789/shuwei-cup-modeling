import io

p = r'E:\数学建模\_swc2026\SWC2026_C\main.tex'
t = io.open(p, encoding='utf-8').read()

subs = [
    ('A dilated temporal\nconvolutional network with \\slotPSegGPUParams{} parameters scores each frame for being a\nboundary',
     'A dilated temporal\nconvolutional network with \\slotPSegGPUParams{} parameters --- in place of a\nstate-space filter over the same frames \\cite{durbin2012} --- scores each frame for being a\nboundary'),
    ('We report no Brier score for this route, and the omission is a finding: the score is a\nranking, not a probability.',
     'We report no Brier score for this route, and the omission is a finding: a Brier score is a\nproper scoring rule and therefore punishes a mis-calibrated probability \\cite{gneiting2007},\nwhereas the weight was built to rank.'),
    ('No Gaussian assumption is made; exchangeability within a mask length is\nthe only requirement, and it is the assumption we check.',
     'No Gaussian assumption is made; exchangeability within a mask length is\nthe only requirement, and it is the assumption we check. This is the split-conformal\nconstruction of \\cite{vovk2005}.'),
    ('due time, a weight, a zone and an item family; its true duration $d$ is never',
     'due time, a weight, a zone and an item family --- single-machine scheduling with release\ndates and due dates \\cite{pinedo2022} --- its true duration $d$ is never'),
    ('under \\eqref{eq:cfprob} that is exactly the condition for re-observing to lose value.',
     'under \\eqref{eq:cfprob} that is exactly the condition for re-observing to lose value, which\nis the value-of-information argument of \\cite{howard1966} stated in this protocol.'),
    # masked observations: missing-data framework
    ('Input-side masking is a missing-data mechanism, not a sensor fault.',
     'Input-side masking is a missing-data mechanism, not a sensor fault, in the sense of\n\\cite{rubin1976} and \\cite{little2019}.'),
    # the adaptive rule reads as dynamic scheduling
    ('The rule is selected on the first fifteen seeds and frozen for the rest.',
     'The rule is selected on the first fifteen seeds and frozen for the rest --- a rescheduling\nrule in the sense surveyed by \\cite{ouelhadj2009}.'),
]

for old, new in subs:
    n = t.count(old)
    print('count=%d anchor=%r' % (n, old[:46]))
    if n != 1:
        print('  MISS -> skipped')
        continue
    t = t.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('written')