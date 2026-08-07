#!/usr/bin/env python3
"""固定事件集(以 H=20 去重)後掃出場期 -> 判斷 H=20 的優勢是真峰還是抽樣假象。
同時檢查現況家族「命中率升但平均報酬=0」的損益結構。"""
import numpy as np
import pandas as pd
import short_engine as E

px = E.load_px()
cot = E.attach_entry(E.load_cot(6), px)
ipos = cot.ipos.values
v = px.values

print("=" * 100)
print("[X1] 固定事件集(pct52>=80,以 H=20 去重,n=89)-> 掃不同出場期")
fwd20 = E.fwd_ret(px, ipos, 20)
valid20 = ~np.isnan(fwd20) & cot.pct52.notna().values
m = (cot.pct52 >= 80).values & valid20
keep = E.dedup(m, ipos, 20)
ev = np.where(keep)[0]
allv = np.where(valid20)[0]
print(f"  固定事件集 n={len(ev)}")
for H in [5, 10, 15, 18, 20, 22, 25, 30, 40, 60]:
    ok = (ipos[ev] + H) < len(v)
    r = v[ipos[ev][ok] + H] / v[ipos[ev][ok]] - 1
    okb = (ipos[allv] + H) < len(v)
    br = v[ipos[allv][okb] + H] / v[ipos[allv][okb]] - 1
    print(f"  出場 H={H:>3}  n={ok.sum():<3} wr={(r>0).mean()*100:>5.1f}% base={(br>0).mean()*100:>5.1f}% "
          f"edge={(r>0).mean()*100-(br>0).mean()*100:>6.1f} avg={r.mean()*100:>6.2f}% base_avg={br.mean()*100:>5.2f}%")
print("  -> 若 edge 在 H=18~30 是平緩高原而非只有 H=20 尖峰,則刀鋒是抽樣假象;反之為過度配適")

print("\n" + "=" * 100)
print("[X2] R1a 損益結構(H=20, n=89):贏面/輸面大小")
ok = (ipos[ev] + 20) < len(v)
r = (v[ipos[ev][ok] + 20] / v[ipos[ev][ok]] - 1) * 100
w, l = r[r > 0], r[r <= 0]
print(f"  贏 {len(w)} 次 中位+{np.median(w):.2f}% 平均+{w.mean():.2f}%")
print(f"  輸 {len(l)} 次 中位{np.median(l):.2f}% 平均{l.mean():.2f}% 最壞{l.min():.2f}%")
print(f"  期望值 {r.mean():.2f}% / 賠率(平均贏/平均輸) {w.mean()/abs(l.mean()):.2f}")
print(f"  賭錯(輸面)中位 {np.median(l):.2f}% 最壞 {l.min():.2f}%")

print("\n" + "=" * 100)
print("[X3] 現況家族損益結構:pct52<=50 & net4連2週正 -> 空,H=10(命中率+12.4 但 avg≈0)")
cd = ((cot.pct52 <= 50) & (cot.net4 > 0) & (cot.net2 > 0)).values
f10 = E.fwd_ret(px, ipos, 10)
val = ~np.isnan(f10) & cot.pct52.notna().values
k2 = E.dedup(cd & val, ipos, 10)
r2 = -f10[k2] * 100
w2, l2 = r2[r2 > 0], r2[r2 <= 0]
print(f"  n={len(r2)} wr={(r2>0).mean()*100:.1f}%")
print(f"  贏 {len(w2)} 次 中位+{np.median(w2):.2f}% 平均+{w2.mean():.2f}%")
print(f"  輸 {len(l2)} 次 中位{np.median(l2):.2f}% 平均{l2.mean():.2f}% 最壞{l2.min():.2f}%")
print(f"  期望值 {r2.mean():.2f}%  -> 命中率高但賠率<1(小賺大賠),不可交易")
