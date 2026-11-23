# Excerpt from code/p1_state.py :: hand_feats
def hand_feats(P, side):
    """P: (N,21,3) already in head frame. Returns (N,D) and names."""
    wrist, thumb_tip, index_tip = P[:, 0], P[:, 4], P[:, 8]
    index_mcp, little_mcp = P[:, 5], P[:, 17]
    mid_mcp = P[:, 9]
    palm_w = np.linalg.norm(index_mcp - little_mcp, axis=1) + 1e-6
    aperture = np.linalg.norm(thumb_tip - index_tip, axis=1) / palm_w
    reach = np.linalg.norm(index_tip - wrist, axis=1) / palm_w
    n = np.cross(index_mcp - wrist, little_mcp - wrist)
    n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    fwd = mid_mcp - wrist
    fwd = fwd / (np.linalg.norm(fwd, axis=1, keepdims=True) + 1e-9)
    v = np.zeros_like(wrist); a = np.zeros_like(wrist)
    for r, g in pd.DataFrame({"rec": REC}).groupby("rec").groups.items():
        ii = np.asarray(g)
        tt = T[ii]
        if len(ii) < 4:
            continue
        for k in range(3):
            v[ii, k] = np.gradient(wrist[ii, k], tt)
            a[ii, k] = np.gradient(v[ii, k], tt)
    feats = np.concatenate([
        wrist, thumb_tip, index_tip, index_mcp, little_mcp,
        aperture[:, None], reach[:, None], palm_w[:, None],
        n, fwd, v, a,
        np.linalg.norm(v, axis=1)[:, None], np.linalg.norm(a, axis=1)[:, None],
    ], axis=1)
    names = ([f"{side}_wrist_{ax}" for ax in "xyz"] +
             [f"{side}_thumbTip_{ax}" for ax in "xyz"] +
             [f"{side}_indexTip_{ax}" for ax in "xyz"] +
             [f"{side}_indexMCP_{ax}" for ax in "xyz"] +
             [f"{side}_littleMCP_{ax}" for ax in "xyz"] +
             [f"{side}_aperture_norm", f"{side}_reach_norm", f"{side}_palm_width",
              f"{side}_normal_x", f"{side}_normal_y", f"{side}_normal_z",
              f"{side}_fwd_x", f"{side}_fwd_y", f"{side}_fwd_z",
              f"{side}_vel_x", f"{side}_vel_y", f"{side}_vel_z",
              f"{side}_acc_x", f"{side}_acc_y", f"{side}_acc_z",
              f"{side}_speed", f"{side}_accnorm"])
    return feats.astype(np.float32), names
