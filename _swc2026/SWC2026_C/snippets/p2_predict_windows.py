# Excerpt from code/p2_predict.py :: windows
def windows(split, L, cap=CAP):
    out = []
    for r in recs[recs.split == split].rec:
        ii = np.where(rec == r)[0]
        F = hand_of(r)[ii, :3]
        bad = (badL[ii] if dom[r] == 0 else badR[ii]).astype(bool)
        ok = ~bad
        run = 0
        starts = []
        for k in range(len(ii)):
            run = run + 1 if ok[k] else 0
            if run >= CTX + L:
                starts.append(k - CTX - L + 1)
        if not starts:
            continue
        starts = np.array(starts)
        stride = max(1, L // 2)
        pick = starts[::stride]
        if len(pick) > cap:
            pick = pick[np.linspace(0, len(pick) - 1, cap).astype(int)]
        for s0 in pick:
            ctx = F[s0:s0 + CTX]
            tgt = F[s0 + CTX:s0 + CTX + L]
            post = F[s0 + CTX + L] if s0 + CTX + L < len(F) else None
            out.append((ctx, tgt, post, r))
    return out
