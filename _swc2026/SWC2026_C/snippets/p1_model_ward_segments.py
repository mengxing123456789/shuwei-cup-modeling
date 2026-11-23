# Excerpt from code/p1_model.py :: ward_segments
def ward_segments(X, K):
    n = len(X)
    if n < 3 or K < 2:
        return np.zeros(n, int)
    C = sparse.diags([np.ones(n - 1), np.ones(n - 1)], [1, -1], shape=(n, n), format="csr")
    lab = AgglomerativeClustering(n_clusters=K, connectivity=C, linkage="ward").fit_predict(X)
    # remove isolated flickers, then relabel contiguous runs
    for _ in range(2):
        for i in range(1, len(lab) - 1):
            if lab[i] != lab[i - 1] and lab[i] != lab[i + 1]:
                lab[i] = lab[i - 1]
    _, runs = np.unique(lab, return_inverse=True)
    # merge non-adjacent repeats of same label by run id
    run_id = np.zeros(len(lab), int); m = 0
    for i in range(1, len(lab)):
        if lab[i] != lab[i - 1]:
            m += 1
        run_id[i] = m
    return run_id
