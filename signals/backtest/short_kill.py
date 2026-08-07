#!/usr/bin/env python3
"""殺 R1a:H 敏感度 + 訊號位移安慰劑 + 隨機安慰劑分布"""
import numpy as np
import pandas as pd
import short_engine as E

px = E.load_px()
cot = E.attach_entry(E.load_cot(6), px)
pd.set_option("display.width", 250)

print("=" * 100)
print("[K1] H 敏感度 (pct52>=80) — H=20 是不是刀鋒?")
for H in [5, 10, 15, 18, 20, 22, 25, 30, 40, 60]:
    r = E.bt("", cot, px, cot.pct52 >= 80, H, +1, "")
    print(f"  H={H:>3}  n={r['n']:<4} wr={r['wr']:<5} base={r['base']:<5} edge={r['edge']:<6} "
          f"avg={r['avg']:<6} p_binom={r['p_binom']:<7} half={r['half']}")

print("\n" + "=" * 100)
print("[K2] 訊號位移安慰劑 (pct52>=80 訊號向後移 k 週) — 真訊號應在 k=0 最強且 k>0 快速衰減")
s = (cot.pct52 >= 80)
for k in [-4, -2, -1, 0, 1, 2, 4, 8]:
    c = s.shift(k).fillna(False)
    r = E.bt("", cot, px, c, 20, +1, "")
    tag = " <= 真訊號" if k == 0 else ""
    print(f"  位移 k={k:>3} 週  n={r['n']:<4} wr={r['wr']:<5} edge={r['edge']:<6} avg={r['avg']:<6} p={r['p_binom']}{tag}")

print("\n" + "=" * 100)
print("[K3] 隨機安慰劑:隨機抽同樣數量的 COT 週(去重後),看 wr=66.3% 有多罕見")
ipos = cot.ipos.values
fwd = E.fwd_ret(px, ipos, 20)
valid = ~np.isnan(fwd) & cot.pct52.notna().values
m = (cot.pct52 >= 80).values & valid
keep = E.dedup(m, ipos, 20)
n_target = int(keep.sum())
obs_wr = (fwd[keep] > 0).mean() * 100
obs_avg = fwd[keep].mean() * 100
vidx = np.where(valid)[0]
rng = np.random.default_rng(42)
wrs, avgs = [], []
for _ in range(5000):
    # 隨機抽同樣多的 valid 週,再套同樣去重規則
    perm = rng.permutation(vidx)
    sel = np.zeros(len(cot), bool); sel[perm] = True
    # 從隨機順序中貪婪取滿足冷卻的 n_target 個
    chosen, last_used = [], []
    for i in perm:
        if all(abs(ipos[i] - u) >= 20 for u in last_used[-40:]):
            chosen.append(i); last_used.append(ipos[i]); last_used.sort()
        if len(chosen) == n_target: break
    rr = fwd[np.array(chosen)]
    wrs.append((rr > 0).mean() * 100); avgs.append(rr.mean() * 100)
wrs, avgs = np.array(wrs), np.array(avgs)
print(f"  觀測 wr={obs_wr:.1f}%  隨機分布 mean={wrs.mean():.1f}% sd={wrs.sd() if hasattr(wrs,'sd') else wrs.std():.1f}%  "
      f"p(隨機>=觀測)={np.mean(wrs >= obs_wr):.4f}")
print(f"  觀測 avg={obs_avg:.2f}%  隨機 mean={avgs.mean():.2f}% sd={avgs.std():.2f}%  "
      f"p(隨機>=觀測)={np.mean(avgs >= obs_avg):.4f}")

print("\n" + "=" * 100)
print("[K4] 空頭分位 vs 淨倉分位:pct52>=80 是否只是 net(淨多)低位的替身?")
net_pct = cot.net.rolling(52).apply(lambda x: (x.iloc[-1] > x.iloc[:-1]).mean() * 100, raw=False) \
    if "net" in cot.columns else None
cot2 = cot.copy()
cot2["net"] = cot2.noncomm_long - cot2.noncomm_short
cot2["netpct52"] = [E.pct_strict(cot2.net.iloc[max(0, i - 51):i + 1]) if i >= 25 else np.nan
                    for i in range(len(cot2))]
for nm, cd in [("net分位<=20 ->多", cot2.netpct52 <= 20),
               ("net分位<=10 ->多", cot2.netpct52 <= 10),
               ("short分位>=80 & net分位<=20", (cot2.pct52 >= 80) & (cot2.netpct52 <= 20)),
               ("short分位>=80 & net分位>20 (剝離net)", (cot2.pct52 >= 80) & (cot2.netpct52 > 20))]:
    r = E.bt(nm, cot2, px, cd, 20, +1, "")
    print(f"  {nm:<34} n={r['n']:<4} wr={r['wr']:<5} base={r['base']:<5} edge={r['edge']:<6} p={r['p_binom']}")
print("  -> 若 short>=80 的優勢在剝離 net 低位後消失,則空頭分位只是淨倉的替身,非獨立訊號")
