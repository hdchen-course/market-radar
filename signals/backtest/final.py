import pandas as pd, numpy as np
from engine import df
from score import *
from score2 import *
px=df.SI; c=pd.read_pickle("/tmp/cot2.pkl")
DI=df.index; CI=c.index
pd.set_option("display.width",300)
ma50=px.rolling(50).mean(); ma200=px.rolling(200).mean(); dev=(px/ma50-1)*100
gsr5=df.GSR.diff(5); G=df.GSR
gz=(df.GSR-df.GSR.rolling(250).mean())/df.GSR.rolling(250).std()
sz=(df.SIHG-df.SIHG.rolling(250).mean())/df.SIHG.rolling(250).std()
hg5=df.HG.pct_change(5)*100; dxy5=df.DXY.pct_change(5)*100
tnx5=df.TNX.diff(5); tip5=df.TIP.pct_change(5)*100; bear=px<ma200

SPEC=[
 # key, name, leg, sig, H, dir, index, gap, mk_sig(門檻函數) or None, center
 ("S1","COT淨多4週變動≥+20,000口 → 空銀","籌碼",c.net4>=20000,60,-1,CI,12,(lambda t:c.net4>=t),20000),
 ("S2","COT淨多52週百分位≥90 → 空銀","籌碼",c.pct52>=90,60,-1,CI,12,(lambda t:c.pct52>=t),90),
 ("S3","金銀比5日≥+2 → 多銀 (不分層)","貨幣",gsr5>=2,20,1,DI,20,(lambda t:gsr5>=t),2),
 ("S3H","金銀比5日≥+2 且 GSR>81.6(高比值端) → 多銀","貨幣",(gsr5>=2)&(G>81.6),20,1,DI,20,(lambda t:(gsr5>=2)&(G>t)),81.6),
 ("S3L","金銀比5日≥+2 且 GSR≤61(低比值端) → 多銀","貨幣",(gsr5>=2)&(G<=61),20,1,DI,20,None,None),
 ("S3M","金銀比5日≥+2 且 GSR 60-75(中間帶) → 多銀","貨幣",(gsr5>=2)&(G>=60)&(G<=75),20,1,DI,20,None,None),
 ("S1b","COT淨多4週變動≥+20,000口 → 空銀 H=20","籌碼",c.net4>=20000,20,-1,CI,4,(lambda t:c.net4>=t),20000),
 ("S2b","COT淨多52週百分位≥90 → 空銀 H=20","籌碼",c.pct52>=90,20,-1,CI,4,(lambda t:c.pct52>=t),90),
 ("S7","跌破100日低 → 多銀(反向)","動能",px<=px.rolling(100).min(),20,1,DI,20,None,None),
 ("S8","跌破50日低 → 多銀(反向) H=60","動能",px<=px.rolling(50).min(),60,1,DI,60,None,None),
 ("S6","COT淨多絕對≥60,000口 → 空銀","籌碼",c.net>=60000,60,-1,CI,12,(lambda t:c.net>=t),60000),
 ("S10","COT未平倉量52週百分位≥90 → 空銀","籌碼",c.oi52>=90,60,-1,CI,12,(lambda t:c.oi52>=t),90),
 ("S4","COT淨多52週百分位≤10 → 多銀","籌碼",c.pct52<=10,60,1,CI,12,None,None),
 ("S9","金銀比 z(250d)≤-2 → 多銀","貨幣",gz<=-2,20,1,DI,20,None,None),
 ("X1","【證偽】乖離MA50≥+25% → 空銀","動能",dev>=25,60,-1,DI,60,(lambda t:dev>=t),25),
 ("X2","【證偽】乖離MA50≥+20% → 空銀","動能",dev>=20,20,-1,DI,20,(lambda t:dev>=t),20),
 ("X3","【證偽】跌破50日低 → 空銀(追空)","動能",px<=px.rolling(50).min(),20,-1,DI,20,None,None),
 ("X4","【證偽】金銀比5日≥+2 → 空銀(方向錯)","貨幣",gsr5>=2,20,-1,DI,20,None,None),
 ("X5","【對照】DXY 5日≤-1.5% → 多銀","貨幣",dxy5<=-1.5,10,1,DI,10,None,None),
 ("X6","【對照】銅5日≥+3% → 多銀","工業",hg5>=3,10,1,DI,10,None,None),
 ("X7","【對照】10Y殖利率5日跌≥15bp → 多銀","貨幣",tnx5<=-0.15,10,1,DI,10,None,None),
 ("X9","【對照】銀銅比 z≥+2 → 空銀","工業",sz>=2,20,-1,DI,20,None,None),
 ("X10","【對照】MA200下且距20日低≥+8% → 空銀","動能",bear&(px/px.rolling(20).min()-1>=0.08),20,-1,DI,20,None,None),
 ("X12","【對照】前日60日高3%內且當日跌≥3% → 空銀","動能",(px.shift(1)>=px.rolling(60).max().shift(1)*0.97)&(px.pct_change()<=-0.03),20,-1,DI,20,None,None),
]
def build(window,lbl):
    rows=[]
    for k,nm,leg,sig,H,d,ix,gap,mk,ctr in SPEC:
        m=evaluate(sig,H,d,ix,gap,window)
        hr,hd=h_robust(sig,H,d,ix,window)
        tr,td=(t_robust(mk,ctr,H,d,ix,window,gap) if mk else (np.nan,{}))
        u=us_v2(m,hr,tr)
        u1=us_score(m)   # lead 原公式
        rows.append(dict(key=k,name=nm,leg=leg,H=H,N=m["N"],hit=m["hit"],base=m["base"],edge=m["edge"],
            avg=m["avg"],med=m["med"],ww_med=m["ww_med"],ww_worst=m["ww_worst"],p_b=m["p_b"],p_t=m["p_t"],
            halves=m["halves"],US_v1=(u1["US"] if u1 else None),US=(u["US"] if u else None),
            hrob=(round(hr,2) if hr==hr else None),trob=(round(tr,2) if tr==tr else None),
            flags=(u["flags"] if u else "-"),sub=(u["sub"] if u else "-"),
            verdict=verdict(u),hdet=str(hd),tdet=str(td)))
    d=pd.DataFrame(rows); d.to_pickle(f"/tmp/final_{lbl}.pkl"); return d
for lbl,w in [("full",W_FULL),("3y",W_3Y)]:
    d=build(w,lbl)
    print("="*40,lbl,"="*40)
    print(d[["key","US_v1","US","verdict","N","hit","base","edge","avg","ww_med","ww_worst","p_b","p_t","hrob","trob","flags"]].sort_values("US",ascending=False,na_position="last").to_string(index=False))
