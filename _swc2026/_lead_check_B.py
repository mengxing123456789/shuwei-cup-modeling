# -*- coding: utf-8 -*-
"""Lead 独立复核：B 题核心几何与精度（用于与 mm-b 的子代理结果对账）。
不追求最终精度，只求出可核对的量级与最优结构。"""
import json, math
import numpy as np

L = 100.0
B = [(22,34,16,26,20),(63,79,59,71,28),(10,24,65,76,12),(72,86,22,34,24),(41,51,38,46,32)]
V0 = [(15,14),(88,10),(14,86),(88,68),(50,93)]
TG = {'T1':(30,40,45),'T2':(150,45,35),'T3':(285,38,55)}
RVEH, HCAM, SPEED = 1.5, 2.0, 3.0
PITCH_LO, PITCH_HI = -10.0, 80.0

def tgt_xy(th,R):
    return (50+R*math.cos(math.radians(th)), 50+R*math.sin(math.radians(th)))
TXY = {k:tgt_xy(v[0],v[1]) for k,v in TG.items()}

def in_field(x,y):
    return RVEH <= x <= L-RVEH and RVEH <= y <= L-RVEH

def in_building(x,y,pad=RVEH):
    for (x0,x1,y0,y1,h) in B:
        if x0-pad < x < x1+pad and y0-pad < y < y1+pad:
            return True
    return False

def seg_box_interval(p,d,box):
    """Liang-Barsky: 参数 t 区间使 p+t*d 落在 box 的 x-y 范围内"""
    x0,x1,y0,y1,h = box
    t0,t1 = 0.0,1.0
    for lo,hi,pi,di in ((x0,x1,p[0],d[0]),(y0,y1,p[1],d[1])):
        if abs(di) < 1e-12:
            if pi < lo or pi > hi: return None
        else:
            a,b = (lo-pi)/di,(hi-pi)/di
            if a>b: a,b = b,a
            t0,t1 = max(t0,a),min(t1,b)
            if t0>t1: return None
    return (t0,t1)

def occluded(px,py,tx,ty,th):
    p=(px,py,HCAM); d=(tx-px,ty-py,th-HCAM)
    for box in B:
        iv = seg_box_interval(p,d,box)
        if iv is None: continue
        t0,t1 = iv
        # 若线段在该 t 区间内任一处的 z <= 楼高，即遮挡（含相切）
        z0,z1 = HCAM+t0*d[2], HCAM+t1*d[2]
        if min(z0,z1) <= box[4] + 1e-12:
            return True
    return False

def pitch_deg(px,py,tx,ty,th):
    r = math.hypot(tx-px,ty-py)
    return math.degrees(math.atan2(th-HCAM, r)) if r>0 else 90.0

def observable(px,py,k):
    tx,ty = TXY[k]; th = TG[k][2]
    if not in_field(px,py) or in_building(px,py): return False
    ang = pitch_deg(px,py,tx,ty,th)
    if ang > PITCH_HI or ang < PITCH_LO: return False
    return not occluded(px,py,tx,ty,th)

# ---------- P1: 可观测域栅格 ----------
step = 0.5
xs = np.arange(RVEH, L-RVEH+1e-9, step)
mask = np.zeros((len(xs),len(xs)),bool)
pitch = np.full((len(xs),len(xs)),np.nan)
for i,x in enumerate(xs):
    for j,y in enumerate(xs):
        if observable(x,y,'T1'):
            mask[i,j]=True
            pitch[i,j]=pitch_deg(x,y,*TXY['T1'],TG['T1'][2])
area = mask.sum()*step*step
print(f"[P1] 栅格 {step} m, 可观测面积 = {area:.1f} m^2 ({area/(L*L)*100:.1f}% of 100x100)")
# 地形约束（仅楼+边界，不看俯仰/遮挡）作对照
foot = np.zeros_like(mask)
for i,x in enumerate(xs):
    for j,y in enumerate(xs):
        foot[i,j] = in_field(x,y) and not in_building(x,y)
print(f"[P1] 仅几何约束(边界+楼)面积 = {foot.sum()*step*step:.1f} m^2")
# 平面阴影（忽略楼高）对照
def occl_planar(px,py,tx,ty):
    d=(tx-px,ty-py)
    for box in B:
        if seg_box_interval((px,py),d,box) is not None: return True
    return False
m2 = np.zeros_like(mask)
for i,x in enumerate(xs):
    for j,y in enumerate(xs):
        if in_field(x,y) and not in_building(x,y):
            ang = pitch_deg(x,y,*TXY['T1'],TG['T1'][2])
            if PITCH_LO<=ang<=PITCH_HI and not occl_planar(x,y,*TXY['T1']):
                m2[i,j]=True
print(f"[P1] 平面阴影模型面积 = {m2.sum()*step*step:.1f} m^2  (三维 vs 平面差 = {(mask.sum()-m2.sum())*step*step:.1f} m^2)")

# Q=1/r 最优站
r = np.hypot(xs[:,None]-TXY['T1'][0], xs[None,:]-TXY['T1'][1])
Q = np.where(mask, 1.0/np.maximum(r,1e-9), -1)
k = np.unravel_index(np.argmax(Q), Q.shape)
bx,by = xs[k[0]], xs[k[1]]
print(f"[P1] Q=1/r 最优站 = ({bx:.2f}, {by:.2f})  r={r[k]:.3f} m  elev={pitch[k]:.3f} deg  Q={Q[k]:.5f} 1/m")
# 约束的紧致性：俯仰上限半径
for kk in TG:
    H = TG[kk][2]
    print(f"     {kk}: H={H} -> 俯仰80° 最小水平距离 = {(H-HCAM)/math.tan(math.radians(80)):.3f} m")

# ---------- P2(1): 双站 DRMS ----------
sig = math.radians(1.0)
reach = SPEED*30.0
best = None
rows=[]
for kk in ['T2']:
    tx,ty = TXY[kk]; th = TG[kk][2]
    for i in range(5):
        for j in range(i+1,5):
            vi,vj = V0[i],V0[j]
            # 只在各自 90m 可达圆内取候选栅格（粗 1m）
            cand_i = [(x,y) for x in np.arange(0,L+1,1.0) for y in np.arange(0,L+1,1.0)
                      if math.hypot(x-vi[0],y-vi[1])<=reach and observable(x,y,kk)]
            cand_j = [(x,y) for x in np.arange(0,L+1,1.0) for y in np.arange(0,L+1,1.0)
                      if math.hypot(x-vj[0],y-vj[1])<=reach and observable(x,y,kk)]
            if not cand_i or not cand_j: continue
            ci = np.array(cand_i); cj = np.array(cand_j)
            ri = np.hypot(ci[:,0]-tx, ci[:,1]-ty); rj = np.hypot(cj[:,0]-tx, cj[:,1]-ty)
            psii = np.arctan2(ty-ci[:,1], tx-ci[:,0]); psij = np.arctan2(ty-cj[:,1], tx-cj[:,0])
            # 粗筛：先各自取 r 最小的 400 个，减少配对
            oi = np.argsort(ri)[:600]; oj = np.argsort(rj)[:600]
            ci,ri,psii = ci[oi],ri[oi],psii[oi]
            cj,rj,psij = cj[oj],rj[oj],psij[oj]
            G = psij[None,:]-psii[:,None]
            s = np.abs(np.sin(G))
            drms = sig*np.sqrt(ri[:,None]**2+rj[None,:]**2)/np.maximum(s,1e-6)
            drms[s<1e-3]=np.inf
            idx = np.unravel_index(np.argmin(drms), drms.shape)
            a,b = ci[idx[0]], cj[idx[1]]
            rows.append(dict(pair=f"V{i+1}-V{j+1}", drms=float(drms[idx]),
                             gamma=float(math.degrees(abs(G[idx]))),
                             r1=float(ri[idx[0]]), r2=float(rj[idx[1]]),
                             s1=[float(a[0]),float(a[1])], s2=[float(b[0]),float(b[1])],
                             t1=float(math.hypot(a[0]-vi[0],a[1]-vi[1])/SPEED),
                             t2=float(math.hypot(b[0]-vj[0],b[1]-vj[1])/SPEED)))
for w in sorted(rows,key=lambda z:z['drms']):
    print(f"[P2] {w['pair']}: DRMS={w['drms']*100:.2f} cm  gamma={w['gamma']:.1f}deg  r1={w['r1']:.1f} r2={w['r2']:.1f}  "
          f"stations=({w['s1'][0]:.0f},{w['s1'][1]:.0f})/({w['s2'][0]:.0f},{w['s2'][1]:.0f})  t={w['t1']:.1f}/{w['t2']:.1f}s")

# ---------- P3: 误差传播 ----------
def sigma_deg(s):
    return math.sqrt(((0.3+0.02*s)/40.0*180/math.pi)**2 + 0.8**2 + 0.6**2)
z = 1.959963985
sm = None
for s in np.arange(0,200,0.01):
    if sigma_deg(s) > 5.0/z: sm = s; break
print(f"[P3] sigma(s=40m的测角)  c.f.  s_max = {sm:.2f} m  (sigma={sigma_deg(sm):.4f} deg, 5={z:.4f}*sigma)")
print(f"[P3] 80 m 时 sigma = {sigma_deg(80):.3f} deg -> 需 sigma<= {5.0/z:.3f}")
coef = 180/math.pi/40.0
lim = math.sqrt((5.0/z)**2-1.0)/coef
print(f"[P3] 约束化为 a+80b <= {lim:.4f} m  (系数 {coef:.5f} deg/m; 名义 a=0.3,b=0.02 -> a+80b={0.3+1.6:.2f} 违反)")

json.dump(dict(area=area, q_opt=[float(bx),float(by),float(r[k]),float(pitch[k])],
               pairs=rows, s_max=float(sm), ab_limit=float(lim)),
          open(r"E:\数学建模\_swc2026\_lead_check_B.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nsaved _lead_check_B.json")