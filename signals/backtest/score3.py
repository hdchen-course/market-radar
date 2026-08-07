"""US 定版 (v3): lead 裁決的4項修正 + Edge<2pp上限49 ; 並保留 reviewer 要求的穩健性紅旗
   兩變體:
     A_pure  = 4修正 + edge<2pp cap  (不含穩健性紅旗)
     B_final = A + 跨H/門檻穩健性紅旗 (reviewer要點2要求的第六維度)
"""
import numpy as np
from score import clamp

def subscores(m):
    edge_s=clamp(m["edge"]/100/0.15)
    # 缺陷3: t檢定單尾
    pb=m["p_b"] if m["p_b"]==m["p_b"] else 1.0
    pt=(m["p_t"]/2 if m["avg"]>0 else 1-m["p_t"]/2) if m["p_t"]==m["p_t"] else 1.0
    pmin=min(pb,pt)
    sig_s=1.0 if pmin<=0.01 else (0.6 if pmin<=0.05 else (0.3 if pmin<=0.10 else 0.0))
    samp_s=clamp(m["N"]/30)
    # 缺陷1: 零敗場以 -30% 代入
    ww=m["ww_worst"] if m["ww_worst"]<0 else -30.0
    tail_s=clamp(1-abs(ww/100)/0.30)
    stab_s=m["stab"] if m["stab"]==m["stab"] else 0.0
    return edge_s,sig_s,samp_s,tail_s,stab_s,pmin

def us_pure(m):
    """A: lead 4修正 + edge<2pp cap, 不含穩健性"""
    if m["N"]==0 or m["hit"]!=m["hit"]: return None
    e,s,n,t,st,pmin=subscores(m)
    us=100*(0.30*e+0.25*s+0.20*n+0.15*t+0.10*st)
    caps=[]
    if m["avg"]<=0: us=min(us,49.0); caps.append("avg≤0")
    if m["N"]<8:    us=min(us,49.0); caps.append("樣本<8")
    if m["edge"]<2: us=min(us,49.0); caps.append("edge<2pp")
    return dict(US=round(us,1),caps=";".join(caps) or "-",
                sub=f"e{e:.2f} s{s:.1f} n{n:.2f} t{t:.2f} st{st:.1f}")

def us_final(m,hrob=np.nan,trob=np.nan):
    """B: A + 穩健性紅旗(reviewer要點2)。穩健性佔15%權重"""
    if m["N"]==0 or m["hit"]!=m["hit"]: return None
    e,s,n,t,st,pmin=subscores(m)
    robs=[r for r in [hrob,trob] if r==r]
    rob_s=float(np.mean(robs)) if robs else 0.5
    core=0.30*e+0.25*s+0.20*n+0.15*t+0.10*st
    us=100*(0.85*core+0.15*rob_s)
    caps=[]
    if m["avg"]<=0: us=min(us,49.0); caps.append("avg≤0")
    if m["N"]<8:    us=min(us,49.0); caps.append("樣本<8")
    if m["edge"]<2: us=min(us,49.0); caps.append("edge<2pp")
    if hrob==hrob and hrob<0.6: us=min(us,49.0); caps.append("跨H不穩")
    if trob==trob and trob<0.5: us=min(us,49.0); caps.append("門檻脆弱")
    return dict(US=round(us,1),rob=round(rob_s,2),caps=";".join(caps) or "-",
                sub=f"e{e:.2f} s{s:.1f} n{n:.2f} t{t:.2f} st{st:.1f} R{rob_s:.2f}")
def vd(us):
    if us is None: return "樣本不足"
    return "可獨立進場" if us>=70 else ("僅輔助" if us>=50 else "不可用")
