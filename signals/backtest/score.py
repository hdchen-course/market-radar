import pandas as pd, numpy as np
from scipy import stats as st
from engine import df
px=df.SI
c=pd.read_pickle("/tmp/cot2.pkl")

W_FULL=(pd.Timestamp("2007-01-02"),pd.Timestamp("2026-08-06"))
W_3Y  =(pd.Timestamp("2023-08-01"),pd.Timestamp("2026-08-06"))

def clamp(x,lo=0,hi=1): return max(lo,min(hi,x))

def evaluate(sig, H, direction, index, gap, window):
    """事件去重(冷卻=gap個index單位)+隔日進場+H交易日出場, 限定 window 內的訊號"""
    lo,hi=window
    s=sig.reindex(index).fillna(False).values
    fwd=(px.shift(-(H+1))/px.shift(-1)).reindex(index)-1
    # 事件去重先在全序列做(避免窗口邊界人為切出新事件), 再篩窗口
    idx=np.where(s)[0]; ev=[];last=-10**9
    for i in idx:
        if i-last>=gap: ev.append(i);last=i
    r=[];dts=[]
    for i in ev:
        d=index[i]
        if lo<=d<=hi and not np.isnan(fwd.iloc[i]):
            r.append(fwd.iloc[i]*direction); dts.append(d)
    r=np.array(r)
    # base rate: 同窗、同gap間隔抽樣的無條件簽名報酬
    mask=(index>=lo)&(index<=hi)
    ab=(fwd*direction)[mask].dropna()
    allr=np.array([ab.iloc[i] for i in range(0,len(ab),gap)])
    out=dict(N=len(r),base=round((allr>0).mean()*100,1) if len(allr) else np.nan)
    if len(r)==0:
        return {**out,"hit":np.nan,"edge":np.nan,"avg":np.nan,"med":np.nan,
                "ww_med":np.nan,"ww_worst":np.nan,"p_b":np.nan,"p_t":np.nan,"halves":"-","stab":np.nan}
    hit=(r>0).mean()*100
    edge=hit-out["base"]
    # 賭錯事件的逆向偏差
    wrong=r[r<=0]
    ww_med=float(np.median(wrong)) if len(wrong) else 0.0
    ww_worst=float(wrong.min()) if len(wrong) else 0.0
    pb=st.binomtest((r>0).sum(),len(r),clamp(out["base"]/100,1e-9,1-1e-9),alternative="greater").pvalue if len(r)>=2 else np.nan
    pt=st.ttest_1samp(r,0).pvalue if len(r)>=3 else np.nan
    # 半樣本: 窗口中點切
    mid=lo+(hi-lo)/2
    h1=np.array([x for x,d in zip(r,dts) if d<mid]); h2=np.array([x for x,d in zip(r,dts) if d>=mid])
    def wr(a): return (a>0).mean()*100 if len(a) else np.nan
    w1,w2=wr(h1),wr(h2)
    if len(h1)==0 or len(h2)==0: stab=np.nan; hs=f"前{'-' if len(h1)==0 else f'{w1:.0f}%/{len(h1)}'} 後{'-' if len(h2)==0 else f'{w2:.0f}%/{len(h2)}'}"
    else:
        a=w1>out["base"]; b=w2>out["base"]
        stab=1.0 if (a and b) else (0.0 if (not a and not b) else 0.5)
        hs=f"前{w1:.0f}%/{len(h1)} 後{w2:.0f}%/{len(h2)}"
    return {**out,"hit":round(hit,1),"edge":round(edge,1),"avg":round(r.mean()*100,2),
            "med":round(float(np.median(r))*100,2),"ww_med":round(ww_med*100,2),
            "ww_worst":round(ww_worst*100,1),"p_b":round(pb,4) if pb==pb else np.nan,
            "p_t":round(pt,4) if pt==pt else np.nan,"halves":hs,"stab":stab}

def us_score(m):
    """lead 指定公式, 照抄"""
    if m["N"]==0 or m["hit"]!=m["hit"]: return None
    edge_s=clamp(m["edge"]/100/0.15)
    ps=[p for p in [m["p_b"],m["p_t"]] if p==p]
    pmin=min(ps) if ps else 1.0
    sig_s=1.0 if pmin<=0.01 else (0.6 if pmin<=0.05 else (0.3 if pmin<=0.10 else 0.0))
    samp_s=clamp(m["N"]/30)
    tail_s=clamp(1-abs(m["ww_worst"]/100)/0.30)
    stab_s=m["stab"] if m["stab"]==m["stab"] else 0.0
    us=100*(0.30*edge_s+0.25*sig_s+0.20*samp_s+0.15*tail_s+0.10*stab_s)
    return dict(US=round(us,1),e=round(edge_s,2),s=round(sig_s,2),n=round(samp_s,2),
                t=round(tail_s,2),st=round(stab_s,2))
def verdict(u):
    if u is None: return "樣本不足"
    us=u["US"] if isinstance(u,dict) else u
    return "可獨立進場" if us>=70 else ("僅輔助" if us>=50 else "不可用")
