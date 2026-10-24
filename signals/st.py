import urllib.request, json
def rma(vals,n):
    r=[sum(vals[:n])/n]
    for v in vals[n:]: r.append((r[-1]*(n-1)+v)/n)
    return r
def st(sym,itv):
    try:
        u=f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval={itv}&limit=320"
        d=json.load(urllib.request.urlopen(u,timeout=10))
        if len(d)<301: return f"{itv}:資料不足({len(d)})"
        H=[float(k[2]) for k in d];L=[float(k[3]) for k in d];C=[float(k[4]) for k in d]
        tr=[H[0]-L[0]]
        for i in range(1,len(d)):
            tr.append(max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1])))
        atr=rma(tr,300)[-1]; hl=(H[-1]+L[-1])/2; up=hl+3*atr; lo=hl-3*atr; c=C[-1]
        d_="LONG" if c>up else ("SHORT" if c<lo else "中性")
        return f"{itv}:{d_}(c{c:.1f}/U{up:.1f}/L{lo:.1f}/ATR{atr:.2f})"
    except Exception as e: return f"{itv}:err"
for s in ["XAUUSDT","XAGUSDT","BTCUSDT","ETHUSDT"]:
    print(s, " | ".join(st(s,i) for i in ["1d","4h","1h"]))
