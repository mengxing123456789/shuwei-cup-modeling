# Excerpt from code/p3_schedule.py :: p_late
def p_late(prefix, x):
    """P(resid > x): empirical survival function, no parameters, no assumed family."""
    a = RES[prefix]
    if len(a) == 0:
        return 0.0
    return float(np.mean(a > x))


REVIEW_BAR = 0.02   # expected gain in weighted on-time probability that pays 1 cost + 1 s
