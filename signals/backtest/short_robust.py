#!/usr/bin/env python3
"""對 R1a(pct52>=80 -> 看多銀)做壓力測試:門檻掃描/落後日/子區間/去重強度/多重檢定"""
import numpy as np
import pandas as pd
import short_engine as E

px = E.load_px()
pd.set_option("display.width", 250)

print("=" * 100)
print("[T1] 門檻掃描 (H=20, dir=+1) — 真機制應隨門檻變嚴而變強")
cot = E.attach_entry(E.load_cot(6), px)
rows = [E.bt(f"pct52>={t}", cot, px, cot.pct52 >= t, 20, +1, "") for t in
        [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]]
print(E.fmt(rows))

print("\n[T2] 門檻 ±25% (80 -> 60 / 100),各 H")
for t in [60, 80, 100]:
    print(E.fmt([E.bt(f"pct52>={t}", cot, px, cot.pct52 >= t, H, +1, "") for H in [10, 20, 60]]))

print("\n" + "=" * 100)
print("[T3] COT 落後天數穩健性 (pct52>=80, H=20) — 若靠越早進場才賺=前視殘留")
for lag in [3, 6, 9, 12, 16, 20]:
    c = E.attach_entry(E.load_cot(lag), px)
    r = E.bt(f"lag={lag}d", c, px, c.pct52 >= 80, 20, +1, "")
    print(f"  lag={lag:>2}d  n={r['n']:<4} wr={r['wr']:<5} base={r['base']:<5} edge={r['edge']:<6} avg={r['avg']:<6} p_binom={r['p_binom']}")

print("\n" + "=" * 100)
print("[T4] 子區間 (pct52>=80, H=20) — 事件年代分布 + 分段命中")
ipos = cot.ipos.values
fwd = E.fwd_ret(px, ipos, 20)
valid = ~np.isnan(fwd) & cot.pct52.notna().values
m = (cot.pct52 >= 80).values & valid
keep = E.dedup(m, ipos, 20)
ev = cot[keep].copy()
ev["ret"] = fwd[keep] * 100
ev["yr"] = ev.entry_date.dt.year
print(ev.groupby(ev.yr // 5 * 5).agg(n=("ret", "size"), wr=("ret", lambda x: round((x > 0).mean() * 100, 1)),
                                     avg=("ret", lambda x: round(x.mean(), 2))).to_string())
print("\n事件年份計數:", ev.yr.value_counts().sort_index().to_dict())
# base rate 同期分段
bs = cot[valid].copy(); bs["ret"] = fwd[valid] * 100; bs["yr"] = bs.entry_date.dt.year
print("\n同期 base (全 COT 週):")
print(bs.groupby(bs.yr // 5 * 5).agg(n=("ret", "size"), wr=("ret", lambda x: round((x > 0).mean() * 100, 1)),
                                     avg=("ret", lambda x: round(x.mean(), 2))).to_string())

print("\n" + "=" * 100)
print("[T5] 三分段(而非二分)是否都同向")
k = len(ev)
for i, (a, b) in enumerate([(0, k // 3), (k // 3, 2 * k // 3), (2 * k // 3, k)]):
    s = ev.ret.iloc[a:b]
    print(f"  第{i+1}段 n={len(s)} wr={round((s>0).mean()*100,1)}% avg={round(s.mean(),2)}% "
          f"{ev.entry_date.iloc[a].date()}~{ev.entry_date.iloc[b-1].date()}")

print("\n" + "=" * 100)
print("[T6] 去重強度加倍(冷卻=2H=40交易日)是否還在")
for H, cd in [(20, 40), (20, 60)]:
    keep2 = E.dedup(m, ipos, cd)
    r = fwd[keep2]
    br = fwd[valid]
    print(f"  H={H} 冷卻={cd}  n={keep2.sum()} wr={round((r>0).mean()*100,1)}% "
          f"base={round((br>0).mean()*100,1)}% avg={round(r.mean()*100,2)}%")

print("\n" + "=" * 100)
print("[T7] 多重檢定校正:本輪共測試多少組合")
print("  R1-R5 主表 15 規則 x 3 個 H = 45 組;加門檻掃描 11 + lag 6 = 62 次檢定")
print("  Bonferroni 校正後 alpha=0.05/45 = 0.0011;R1a H=20 p_binom=0.0078 -> 未達標")
print("  即使只算 15 個「事前」規則家族:0.05/15 = 0.0033 -> 仍未達標")

print("\n" + "=" * 100)
print("[T8] 現況條件(pct52=45.1, net4=+2660, 低基期加碼)最近的可比事件")
cur = cot[(cot.pct52.between(30, 60)) & (cot.net4 > 1500)]
print(f"  歷史可比週數 = {len(cur)}(未去重)")
print(cot[["date", "noncomm_short", "pct52", "net4", "short_pct_oi"]].tail(4).to_string(index=False))
