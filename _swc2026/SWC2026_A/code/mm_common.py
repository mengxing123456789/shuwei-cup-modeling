# -*- coding: utf-8 -*-
"""
SWC2026 A 题公共模块：参数、数据装载、JSON 落盘（带 _meta）。

单位约定（与题面 Appendix A/B 一致）：
    压力 MPa、长度 m、时间 d、渗透率 mD、黏度 mPa·s、体积 m^3、金额 CNY。
    进入 PDE 时在函数内部转 SI（Pa、s、m^2、Pa·s）。
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
FIG = os.path.join(ROOT, 'figures')
PROBLEM = os.path.join(ROOT, 'problem')
XLSX = (r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛'
        r'（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx')

CASE_KEYS = ['Case1', 'Case2', 'Case3']
CASE_FULL = {
    'Case1': 'Case1_low-permeability high-stress',
    'Case2': 'Case2_medium-permeability low-stress',
    'Case3': 'Case3_high-permeability complex fractures',
}
CASE_CN = {
    'Case1': '低渗-高应力',
    'Case2': '中渗-低应力',
    'Case3': '高渗-复杂天然裂缝',
}

# ---------------------------------------------------------------- Appendix A.1
GEO = {
    'Case0': dict(Hd=3000, h=20, p0=45, T=110, km=0.10, phi0=0.10, E=30, nu=0.23,
                  sv=75, sH=62, sh=52, Gf=0.020, pf=60.0, pmax=57,
                  rho_r=2500, alpha_b=0.80, gamma_k=0.05, cphi=6e-4,
                  ed=0.005, bd=100),
    'Case1': dict(Hd=3200, h=20, p0=50, T=120, km=0.03, phi0=0.08, E=38, nu=0.25,
                  sv=80, sH=66, sh=58, Gf=0.021, pf=67.2, pmax=60,
                  rho_r=2500, alpha_b=0.85, gamma_k=0.08, cphi=7e-4,
                  ed=0.004, bd=120),
    'Case2': dict(Hd=3000, h=20, p0=45, T=110, km=0.10, phi0=0.10, E=30, nu=0.23,
                  sv=75, sH=62, sh=52, Gf=0.020, pf=60.0, pmax=57,
                  rho_r=2500, alpha_b=0.80, gamma_k=0.04, cphi=6e-4,
                  ed=0.005, bd=100),
    'Case3': dict(Hd=3000, h=20, p0=48, T=100, km=0.50, phi0=0.13, E=24, nu=0.20,
                  sv=72, sH=58, sh=48, Gf=0.022, pf=66.0, pmax=60,
                  rho_r=2500, alpha_b=0.75, gamma_k=0.02, cphi=5e-4,
                  ed=0.006, bd=80),
}

# ---------------------------------------------------------------- Appendix A.2
FLUID = {
    'Case0': dict(rho_o=800, mu_o=2.0, rho_w=1000, mu_w=0.35, co=10e-4, cw=5e-4,
                  Sw0=0.25, Swr=0.20, Sor=0.20, kro0=0.90, krw0=0.30, no=3.0, nw=2.5,
                  Ac=0.5, rhoCO2ref=850, Ho=0.006, Hw=8e-4, bsw=0.8, mmu=3.0,
                  D_co2o=1e-9, D_co2w=2e-9, dn=25, Cn=1.0, Dn=5e-10, Kd=0.01,
                  asig=0.3, atheta=15),
    'Case1': dict(rho_o=810, mu_o=3.0, rho_w=1010, mu_w=0.40, co=10e-4, cw=5e-4,
                  Sw0=0.22, Swr=0.20, Sor=0.20, kro0=0.90, krw0=0.30, no=3.0, nw=2.5,
                  Ac=0.6, rhoCO2ref=850, Ho=0.006, Hw=8e-4, bsw=0.8, mmu=3.0,
                  D_co2o=1e-9, D_co2w=2e-9, dn=25, Cn=1.0, Dn=5e-10, Kd=0.01,
                  asig=0.3, atheta=15),
    'Case2': dict(rho_o=800, mu_o=2.0, rho_w=1000, mu_w=0.35, co=10e-4, cw=5e-4,
                  Sw0=0.25, Swr=0.20, Sor=0.20, kro0=0.90, krw0=0.30, no=3.0, nw=2.5,
                  Ac=0.5, rhoCO2ref=850, Ho=0.006, Hw=8e-4, bsw=0.8, mmu=3.0,
                  D_co2o=1e-9, D_co2w=2e-9, dn=25, Cn=1.0, Dn=5e-10, Kd=0.01,
                  asig=0.3, atheta=15),
    'Case3': dict(rho_o=790, mu_o=1.5, rho_w=1000, mu_w=0.30, co=10e-4, cw=5e-4,
                  Sw0=0.28, Swr=0.20, Sor=0.20, kro0=0.90, krw0=0.30, no=3.0, nw=2.5,
                  Ac=0.4, rhoCO2ref=850, Ho=0.006, Hw=8e-4, bsw=0.8, mmu=3.0,
                  D_co2o=1e-9, D_co2w=2e-9, dn=25, Cn=1.0, Dn=5e-10, Kd=0.01,
                  asig=0.3, atheta=15),
}

# ---------------------------------------------------------------- Appendix A.3
FRAC = {
    'Case0': dict(Lf=120, hf=20, wf=4.0, kf=5000, phif=0.30, rnf=0.0,
                  qinj=300, Vinj=3000, fCO2=0.5, ts=30, tau_inj=0, pwf=35, Tprod=360),
    'Case1': dict(Lf=100, hf=20, wf=3.0, kf=3000, phif=0.30, rnf=0.0,
                  qinj=300, Vinj=3000, fCO2=0.5, ts=30, tau_inj=0, pwf=35, Tprod=360),
    'Case2': dict(Lf=120, hf=20, wf=4.0, kf=5000, phif=0.30, rnf=0.01,
                  qinj=300, Vinj=3000, fCO2=0.5, ts=30, tau_inj=0, pwf=35, Tprod=360),
    'Case3': dict(Lf=140, hf=20, wf=5.0, kf=8000, phif=0.35, rnf=0.08,
                  qinj=300, Vinj=3000, fCO2=0.5, ts=30, tau_inj=0, pwf=35, Tprod=360),
}

# ---------------------------------------------------------------- Appendix B.1
ECON = dict(
    Poil=3396.0,          # CNY/m3   (75 USD/bbl x 7.20 / 0.159)
    cnano=200.0,          # CNY/kg
    cCO2=300.0,           # CNY/t
    cinj=30e4,            # CNY/d
    csoak=3e4,            # CNY/d
    Cfrac=120e4,          # CNY/well, day 0
    cprod=350.0,          # CNY/m3 oil
    cwater=25.0,          # CNY/m3 water
    r=0.08,               # 1/yr, 365 d/yr
)
NANO_LIMIT_T = 30.0       # t per well treatment
DUR_LIMIT = 90.0          # injection + soaking upper limit, d

BOUNDS = dict(
    Cn=(0.5, 1.5), qinj=(100.0, 800.0), Vinj=(1000.0, 5000.0),
    fCO2=(0.2, 0.8), ts=(5.0, 60.0), tau_inj=(0.0, 15.0),
    pmax_equip=60.0,
)


# ================================================================ helpers
def case_params(case):
    """Case1/2/3 的 A.1+A.2+A.3 合并参数（深拷贝）。"""
    p = {}
    p.update(GEO[case])
    p.update(FLUID[case])
    p.update(FRAC[case])
    return p


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _now():
    return datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00')


def _clean_nan(o):
    """NaN / ±Inf -> None，保证 JSON 合规；同时把 numpy 标量转成 python 标量。"""
    if isinstance(o, dict):
        return {k: _clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean_nan(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (f != f or f in (float('inf'), float('-inf'))) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return [_clean_nan(v) for v in o.tolist()]
    return o


def save_json(name, payload, script, inputs=None):
    """写 data/<name>.json，自动补 _meta。"""
    os.makedirs(DATA, exist_ok=True)
    rec = {'_meta': {
        'script': os.path.basename(script),
        'script_sha256': sha256_file(script) if os.path.exists(script) else None,
        'run_at': _now(),
        'python': sys.version.split()[0],
        'numpy': np.__version__,
        'pandas': pd.__version__,
        'host': platform.node(),
        'inputs': {os.path.basename(k): v for k, v in (inputs or {}).items()},
    }}
    rec.update(payload)
    rec = _clean_nan(rec)
    path = os.path.join(DATA, name + '.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1, allow_nan=False)
    return path


def input_hashes():
    return {XLSX: sha256_file(XLSX)}


def load_production():
    """附件 C → 长表 DataFrame，附列 Case / gid（场景×浓度×浸泡）。"""
    df = pd.read_excel(XLSX)
    df['Case'] = df.Case_ID.str.slice(0, 5)
    df = df.rename(columns={'Nano_Concentration_wt%': 'Cn', 'Soak_Time_Days': 'ts',
                             'Production_Day': 'day', 'Oil_Rate_m3_d': 'q',
                             'Cum_Oil_m3': 'cum', 'BHP_MPa': 'bhp'})
    df['gid'] = (df.Case + '|' + df.Cn.map(lambda v: f'{v:.1f}')
                 + '|' + df.ts.astype(int).astype(str))
    return df


def arps_exp(t, qi, D):
    return qi * np.exp(-D * t)


def arps_hyp(t, qi, D, b):
    return qi / np.power(1.0 + b * D * t, 1.0 / b)


def arps_stretch(t, qi, tau, n):
    return qi * np.exp(-np.power(t / tau, n))


def soft_exit(t, qi, D, tc, w):
    """平滑截断：t>tc 后按 logistic 衰减到 0（处理生产末段 q→0）。"""
    return qi * np.exp(-D * t) / (1.0 + np.exp((t - tc) / w))


# ================================================================ 数值工具
# 本机 numpy.polyfit / numpy.corrcoef 会触发原生崩溃 0xC06D007F（无栈），
# 统一改用手写法方程与手写相关系数，见 out/14-ops 记录。
def ols_slope(x, y):
    """一元最小二乘 y = a + b x，返回 (b, a, r2)。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xm = x.mean()
    ym = y.mean()
    sxx = float(np.sum((x - xm) ** 2))
    sxy = float(np.sum((x - xm) * (y - ym)))
    b = sxy / sxx
    a = ym - b * xm
    ss = float(np.sum((y - (a + b * x)) ** 2))
    sst = float(np.sum((y - ym) ** 2))
    return b, a, (1.0 - ss / sst if sst > 0 else np.nan)


def corr(x, y):
    """皮尔逊相关系数（手写，避开 numpy.corrcoef）。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xm = x - x.mean()
    ym = y - y.mean()
    den = np.sqrt(float(np.sum(xm * xm)) * float(np.sum(ym * ym)))
    return float(np.sum(xm * ym) / den) if den > 0 else np.nan