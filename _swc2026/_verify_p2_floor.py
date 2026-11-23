# -*- coding: utf-8 -*-
"""Lead 复核 B:P2(1) 声称的 DRMS 下界可达站对，重点看视线与楼顶的余隙。"""
import math
B=[(22,34,16,26,20),(63,79,59,71,28),(10,24,65,76,12),(72,86,22,34,24),(41,51,38,46,32)]
T2=(50+45*math.cos(math.radians(150)), 50+45*math.sin(math.radians(150)), 35.0)
S1=(6.007,75.4392); S2=(13.9681,77.5219); HC=2.0
print('T2 =',tuple(round(v,4) for v in T2))
def geom(s,name):
    r=math.hypot(T2[0]-s[0],T2[1]-s[1]); 
    el=math.degrees(math.atan2(T2[2]-HC,r))
    print('%-3s (%.4f,%.4f) r=%.4f elev=%.4f'%(name,s[0],s[1],r,el))
    # 视线与各楼盒的最近余隙（以楼顶为基准，竖直方向）
    p=(s[0],s[1],HC); d=(T2[0]-s[0],T2[1]-s[1],T2[2]-HC)
    for (x0,x1,y0,y1,h) in B:
        t0,t1=0.0,1.0; ok=True
        for lo,hi,pi,di in ((x0,x1,p[0],d[0]),(y0,y1,p[1],d[1])):
            if abs(di)<1e-12:
                if pi<lo or pi>hi: ok=False;break
            else:
                a,b=(lo-pi)/di,(hi-pi)/di
                if a>b: a,b=b,a
                t0,t1=max(t0,a),min(t1,b)
                if t0>t1: ok=False;break
        if not ok: continue
        zmin=min(HC+t0*d[2], HC+t1*d[2])
        print('    crosses box h=%2d  t=[%.4f,%.4f]  zmin=%.6f  余隙=%+.6f m'%(h,t0,t1,zmin,zmin-h))
for s,n in ((S1,'V3'),(S2,'V5')): geom(s,n)
u1=(T2[0]-S1[0],T2[1]-S1[1]); u2=(T2[0]-S2[0],T2[1]-S2[1])
c=(u1[0]*u2[0]+u1[1]*u2[1])/(math.hypot(*u1)*math.hypot(*u2))
print('cos(gamma)=%.10f  gamma=%.6f deg'%(c, math.degrees(math.acos(max(-1,min(1,c))))))
r1=math.hypot(*u1); r2=math.hypot(*u2); sig=math.radians(1.0)
g=math.acos(max(-1,min(1,c)))
print('DRMS=%.6f m  (closed form %.6f)'%(sig*math.hypot(r1,r2)/abs(math.sin(g)), sig*math.hypot(r1,r2)/abs(math.sin(g))))
print('baseline=%.6f m'%math.hypot(S1[0]-S2[0],S1[1]-S2[1]))
print('r_min(T2)=(H-2)/tan80=%.6f'%((35-2)/math.tan(math.radians(80))))