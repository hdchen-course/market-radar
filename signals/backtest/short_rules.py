#!/usr/bin/env python3
"""跑候選規則:空頭分位/趨勢 -> 白銀後續走勢"""
import numpy as np
import pandas as pd
import short_engine as E

px = E.load_px()
cot = E.attach_entry(E.load_cot(6), px)
P, N4, N8, S = cot.pct52, cot.net4, cot.net8, cot.noncomm_short
PP, PM8 = cot.pct52_prev, cot.pct52_max8

HS = [10, 20, 60]
rows = []


def R(name, cond, direction, desc):
    for H in HS:
        rows.append(E.bt(name, cot, px, cond, H, direction, desc))


# R1 空頭分位極高 -> 看多銀(擁擠空=軋空燃料)
R("R1a pct52>=80 ->多", P >= 80, +1, "pct52>=80")
R("R1b pct52>=90 ->多", P >= 90, +1, "pct52>=90")
R("R1c pct52>=95 ->多", P >= 95, +1, "pct52>=95")
# R2 空頭分位極低 -> 看空銀(無軋空燃料)
R("R2a pct52<=20 ->空", P <= 20, -1, "pct52<=20")
R("R2b pct52<=10 ->空", P <= 10, -1, "pct52<=10")
R("R2c pct52<=20 ->多", P <= 20, +1, "pct52<=20 反向檢")
# R3 空頭見頂回落(高位開始減)-> 軋空尾聲/價格見頂? 兩個方向都測
R("R3a 高位轉降->多", (PM8 >= 80) & (P < 60) & (N4 < 0), +1, "pct52_max8>=80 & pct52<60 & net4<0")
R("R3b 高位轉降->空", (PM8 >= 80) & (P < 60) & (N4 < 0), -1, "同上,反向")
R("R3c pct52自>=80回落->多", (PP >= 80) & (P < 80), +1, "前週pct52>=80 且本週<80")
# R4 低基期加碼(現況:分位低但4週在增)
R("R4a pct52<=40&net4>0->空", (P <= 40) & (N4 > 0), -1, "pct52<=40 & net4>0")
R("R4b pct52<=40&net4>0->多", (P <= 40) & (N4 > 0), +1, "同上,反向")
R("R4c pct52<=50&net4>1500->空", (P <= 50) & (N4 > 1500), -1, "pct52<=50 & net4>+1500")
# R5 空頭4週變化方向
R("R5a net4>0 ->空", N4 > 0, -1, "net4>0(空單增)")
R("R5b net4<0 ->多", N4 < 0, +1, "net4<0(空單減)")
R("R5c net8>0 ->空", N8 > 0, -1, "net8>0")

out = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(E.fmt(rows))
print("\n--- 半樣本細節 (wr%, avg%, n) ---")
for r in rows:
    if r["n"] >= 8:
        print(f"{r['name']:<26} H={r['H']:<3} n={r['n']:<4} h1={r['h1']} h2={r['h2']} {r['half']}  {r['first']}~{r['last']}")
out.to_csv("/tmp/short_rules_out.csv", index=False)
