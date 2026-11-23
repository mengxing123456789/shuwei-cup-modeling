# -*- coding: utf-8 -*-
"""P1 可观测面积：网格收敛 + 口径（车体净距 1.5 m vs 相机点）对照"""
import math, json, sys
L=100.0
B=[(22,34,16,26,20),(63,79,59,71,28),(10,24,65,76,12),(72,86,22,34,24),(41,51,38,46,32)]
T=(30,40,45); TH=T[2]
TX,TY=50+T[1]*math.cos(math.radians(T[0])), 50+T[1]*math.sin(math.radians(T[0]))
HCAM=2.0; RV=1.5

def seg_box(p,d,box):
    x0,x1,y0,y1,h=box; t0,t1=0.0,1.0
    for lo,hi,pi,di in ((x0,x1,p[0],d[0]),(y0,y1,p[1],d[1])):
        if abs(di)<1e-12:
            if pi<lo or pi>hi: return None
        else:
            a,b=(lo-pi)/di,(hi-pi)/di
            if a>b: a,b=b,a
            t0,t1=max(t0,a),min(t1,b)
            if t0>t1: return None
    return (t0,t1)

def occl(px,py):
    p=(px,py,HCAM); d=(TX-px,TY-py,TH-HCAM)
    for box in B:
        iv=seg_box(p,d,box)
        if iv is None: continue
        z0,z1=HCAM+iv[0]*d[2], HCAM+iv[1]*d[2]
        if min(z0,z1)<=box[4]+1e-12: return True
    return False

def area(step, pad, rv):
    n=0; tot=0
    x=rv
    while x<=L-rv+1e-9:
        y=rv
        while y<=L-rv+1e-9:
            tot+=1
            ok=True
            for (x0,x1,y0,y1,h) in B:
                if x0-pad<=x<=x1+pad and y0-pad<=y<=y1+pad: ok=False;break
            if ok:
                r=math.hypot(TX-x,TY-y)
                el=math.degrees(math.atan2(TH-HCAM,r)) if r>0 else 90.0
                if -10<=el<=80 and not occl(x,y): n+=1
            y+=step
        x+=step
    return n*step*step, tot

out=[]
for step in (1.0,0.5,0.25):
    for pad,tag in ((RV,'车体净距1.5m'),(0.0,'相机点不入楼')):
        a,tot=area(step,pad,RV)
        out.append({'step':step,'caliber':tag,'area_m2':round(a,1),'pct':round(a/(L*L)*100,2)})
        print('step %.2f  %-12s  area %.1f m2  %.2f%%'%(step,tag,a,a/(L*L)*100),flush=True)
json.dump(out,open(r'E:\数学建模\_swc2026\_p1_grid.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)