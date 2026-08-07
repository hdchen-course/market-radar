"""US v2: 在 lead 原公式上加 (a)跨H穩健性 (b)門檻鄰域穩健性 兩個紅旗扣分"""
import pandas as pd, numpy as np
from engine import df
from score import *
px=df.SI; c=pd.read_pickle("/tmp/cot2.pkl")

def h_robust(sig,H0,d,ix,window,Hs=None):
    """跨H穩健性: p_b<=0.05 的H佔比 + edge>0佔比 + avg>0佔比 的平均"""
    Hs=Hs or [10,20,30,40,60,80]
    pb=[];eg=[];av=[]
    for H in Hs:
        m=evaluate(sig,H,d,ix,max(2,H//5) if ix is not df.index else H,window)
        if m["N"]>=3 and m["p_b"]==m["p_b"]:
            pb.append(m["p_b"]<=0.05); eg.append(m["edge"]>0); av.append(m["avg"]>0)
    if not pb: return np.nan,{}
    sc=(np.mean(pb)+np.mean(eg)+np.mean(av))/3
    return sc,dict(p_ok=f"{np.mean(pb):.0%}",edge_ok=f"{np.mean(eg):.0%}",avg_ok=f"{np.mean(av):.0%}")

def t_robust(mk_sig,center,H,d,ix,window,gap,rel=0.25):
    """門檻鄰域穩健性: 門檻±25% 內 HitRate 相對中心的最小保留率"""
    ths=[center*(1+f) for f in [-rel,-rel/2,0,rel/2,rel]]
    hits=[];ns=[]
    for th in ths:
        m=evaluate(mk_sig(th),H,d,ix,gap,window)
        if m["N"]>=3: hits.append(m["hit"]); ns.append(m["N"])
    if len(hits)<3: return np.nan,{}
    ctr=evaluate(mk_sig(center),H,d,ix,gap,window)["hit"]
    if ctr!=ctr or ctr<=0: return np.nan,{}
    keep=min(hits)/ctr
    return clamp((keep-0.7)/0.3),dict(hit_range=f"{min(hits):.1f}-{max(hits):.1f}%",center=f"{ctr:.1f}%",keep=f"{keep:.0%}")

def us_v2(m,hrob=np.nan,trob=np.nan):
    """US v2 = 原五子分(權重壓縮至0.85) + 0.15*穩健性 ; 再套硬性上限"""
    if m["N"]==0 or m["hit"]!=m["hit"]: return None
    edge_s=clamp(m["edge"]/100/0.15)
    pb=m["p_b"] if m["p_b"]==m["p_b"] else 1.0
    pt=(m["p_t"]/2 if m["avg"]>0 else 1-m["p_t"]/2) if m["p_t"]==m["p_t"] else 1.0
    pmin=min(pb,pt)
    sig_s=1.0 if pmin<=0.01 else (0.6 if pmin<=0.05 else (0.3 if pmin<=0.10 else 0.0))
    samp_s=clamp(m["N"]/30)
    ww=m["ww_worst"] if m["ww_worst"]<0 else -30.0
    tail_s=clamp(1-abs(ww/100)/0.30)
    stab_s=m["stab"] if m["stab"]==m["stab"] else 0.0
    robs=[r for r in [hrob,trob] if r==r]
    rob_s=np.mean(robs) if robs else 0.5   # 無法測時給中性0.5
    core=0.30*edge_s+0.25*sig_s+0.20*samp_s+0.15*tail_s+0.10*stab_s
    us=100*(0.85*core+0.15*rob_s)
    flags=[]
    if m["avg"]<=0: us=min(us,49.0); flags.append("平均報酬≤0")
    if m["N"]<8:    us=min(us,49.0); flags.append("樣本<8")
    if hrob==hrob and hrob<0.6: us=min(us,49.0); flags.append("跨H不穩")
    if trob==trob and trob<0.5: us=min(us,49.0); flags.append("門檻脆弱")
    return dict(US=round(us,1),rob=round(rob_s,2),flags=";".join(flags) or "-",
                sub=f"e{edge_s:.2f} s{sig_s:.1f} n{samp_s:.2f} t{tail_s:.2f} st{stab_s:.1f} R{rob_s:.2f}")
