#!/usr/bin/env python3
"""最終裁決:嚴格 out-of-sample + 現況條件(低基期加碼)的誠實結論"""
import numpy as np
import pandas as pd
import short_engine as E

px = E.load_px()
cot = E.attach_entry(E.load_cot(6), px)
ipos = cot.ipos.values


def run(cond, H, direction, lo=None, hi=None):
    fwd = E.fwd_ret(px, ipos, H)
    valid = ~np.isnan(fwd) & cot.pct52.notna().values
    if lo is not None:
        win = (cot.entry_date >= lo).values & (cot.entry_date < hi).values
        valid = valid & win
    m = (cond.values if isinstance(cond, pd.Series) else cond) & valid
    keep = E.dedup(m, ipos, H)
    r = fwd[keep] * direction
    br = fwd[valid] * direction
    if len(r) == 0:
        return None
    return dict(n=len(r), wr=round((r > 0).mean() * 100, 1), base=round((br > 0).mean() * 100, 1),
                avg=round(r.mean() * 100, 2), bavg=round(br.mean() * 100, 2))


print("=" * 100)
print("[F1] 嚴格 OOS:2000-2012 當『發現期』,2013-2026 當『驗證期』(pct52>=80, 各 H)")
for H in [10, 20, 60]:
    a = run(cot.pct52 >= 80, H, +1, pd.Timestamp("2000-01-01"), pd.Timestamp("2013-01-01"))
    b = run(cot.pct52 >= 80, H, +1, pd.Timestamp("2013-01-01"), pd.Timestamp("2027-01-01"))
    print(f"  H={H:<3} IS  n={a['n']:<3} wr={a['wr']:<5} base={a['base']:<5} edge={round(a['wr']-a['base'],1):<6} avg={a['avg']}")
    print(f"       OOS n={b['n']:<3} wr={b['wr']:<5} base={b['base']:<5} edge={round(b['wr']-b['base'],1):<6} avg={b['avg']}")

print("\n" + "=" * 100)
print("[F2] 只看『H=20 這個刀鋒』在 OOS 是否還是刀鋒")
for H in [10, 15, 18, 20, 22, 25, 30]:
    b = run(cot.pct52 >= 80, H, +1, pd.Timestamp("2013-01-01"), pd.Timestamp("2027-01-01"))
    print(f"  OOS H={H:<3} n={b['n']:<3} wr={b['wr']:<5} base={b['base']:<5} edge={round(b['wr']-b['base'],1)}")

print("\n" + "=" * 100)
print("[F3] 現況條件家族(pct52 中低 + net4 正)— 使用者今天面對的狀況")
for nm, cd in [("pct52 30-60 & net4>+1500", (cot.pct52.between(30, 60)) & (cot.net4 > 1500)),
               ("pct52<=50 & net4>+2000", (cot.pct52 <= 50) & (cot.net4 > 2000)),
               ("pct52<=50 & net4連2週正", (cot.pct52 <= 50) & (cot.net4 > 0) & (cot.net2 > 0))]:
    for H in [10, 20]:
        for d, dl in [(+1, "多"), (-1, "空")]:
            r = run(cd, H, d)
            if r:
                print(f"  {nm:<26} H={H:<3} {dl}  n={r['n']:<3} wr={r['wr']:<5} base={r['base']:<5} "
                      f"edge={round(r['wr']-r['base'],1):<6} avg={r['avg']}")

print("\n" + "=" * 100)
print("[F4] 空頭佔 OI 比(short_pct_oi,絕對規模而非分位)有沒有預測力")
q = cot.short_pct_oi
for nm, cd in [("short/OI>=20%", q >= 20), ("short/OI>=25%", q >= 25),
               ("short/OI<=10%", q <= 10), ("short/OI<=8%", q <= 8)]:
    for H in [20]:
        for d, dl in [(+1, "多"), (-1, "空")]:
            r = run(cd, H, d)
            if r and r["n"] >= 10:
                print(f"  {nm:<16} H={H} {dl}  n={r['n']:<3} wr={r['wr']:<5} base={r['base']:<5} "
                      f"edge={round(r['wr']-r['base'],1):<6} avg={r['avg']}")
print(f"\n  現況 short/OI = {cot.short_pct_oi.iloc[-1]:.1f}%  "
      f"(歷史分布 p10={q.quantile(.1):.1f} p50={q.quantile(.5):.1f} p90={q.quantile(.9):.1f})")
