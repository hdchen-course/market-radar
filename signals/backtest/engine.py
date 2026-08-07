import pickle, pandas as pd, numpy as np
d=pickle.load(open("/tmp/px.pkl","rb"))
C=d["close"].copy()
# 排除今日盤中未收盤 bar
C=C[C.index<=pd.Timestamp("2026-08-06")]
C=C.rename(columns={"DX-Y.NYB":"DXY","SI=F":"SI","GC=F":"GC","HG=F":"HG","^TNX":"TNX","^GSPC":"SPX","CL=F":"CL","^VIX":"VIX"})
SI=C.SI.dropna()
def ffb(s): return s.reindex(SI.index).ffill()
df=pd.DataFrame({"SI":SI,"GC":ffb(C.GC),"HG":ffb(C.HG),"DXY":ffb(C.DXY),"TNX":ffb(C.TNX),"SPX":ffb(C.SPX),"VIX":ffb(C.VIX),"SLV":ffb(C.SLV),"TIP":ffb(C.TIP)})
df=df.dropna(subset=["SI","GC","DXY"])
df["GSR"]=df.GC/df.SI            # 金銀比
df["SIHG"]=df.SI/df.HG           # 銀銅比
df["r"]=df.SI.pct_change()
pickle.dump(df,open("/tmp/df.pkl","wb"))

def bt(name, sig, H=10, direction=1, data=None):
    """sig: 布林 Series，True=訊號日 t。進場 t+1 收盤，出場 t+1+H 收盤。
       direction 1=看多銀, -1=看空銀。成功=方向正確。"""
    x=(data if data is not None else df)
    px=x.SI
    fwd=px.shift(-(H+1))/px.shift(-1)-1     # t+1 進 -> t+1+H 出
    s=sig.reindex(x.index).fillna(False)
    valid=fwd.notna()
    hit=((fwd*direction)>0)
    n=int((s&valid).sum())
    if n==0: return dict(name=name,H=H,n=0,wr=np.nan,base=np.nan,edge=np.nan,avg=np.nan,bavg=np.nan)
    wr=hit[s&valid].mean()*100
    base=hit[valid].mean()*100
    avg=(fwd[s&valid]*direction).mean()*100
    bavg=(fwd[valid]*direction).mean()*100
    return dict(name=name,H=H,n=n,wr=round(wr,1),base=round(base,1),edge=round(wr-base,1),
                avg=round(avg,2),bavg=round(bavg,2),med=round(float((fwd[s&valid]*direction).median()*100),2))
if __name__=="__main__":
    print(df.tail(3).to_string())
    print("span:",df.index[0].date(),df.index[-1].date(),len(df))
