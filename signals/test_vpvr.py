"""test_vpvr.py — vpvr.py 單元測試（純標準庫、確定性合成輸入驗證 POC/VA/HVN/LVN 數學）。
跑法：python3 test_vpvr.py"""
import vpvr as V

_fail = 0


def check(name, cond):
    global _fail
    print(("  ok  " if cond else "FAIL  ") + name)
    if not cond:
        _fail += 1


# 1) 集中單價：所有量壓在同一價 → POC 應在該價、VA 收斂到該處
H = [10, 10, 10, 10]; L = [10, 10, 10, 10]; C = [10, 10, 10, 10]; Vv = [5, 5, 5, 5]
r = V.vpvr(H, L, C, Vv, bins=10)
check("全平輸入 POC=該價", r["poc"] == 10 and r["vah"] == 10 and r["val"] == 10)

# 2) 已知峰：在 100 附近堆大量、兩側少量 → POC bin 應含 100
H = [101, 101, 101, 106, 96]
L = [99, 99, 99, 104, 94]
C = [100, 100, 100, 105, 95]
Vv = [1000, 1000, 1000, 10, 10]   # 100 附近量壓倒性
r = V.vpvr(H, L, C, Vv, bins=20)
check("POC 落在高量價區(99~101)", 99 <= r["poc"] <= 101)
check("VAL<=POC<=VAH", r["val"] <= r["poc"] <= r["vah"])
check("total_vol 守恆", abs(r["total_vol"] - sum(Vv)) < 1e-6)

# 3) Value Area 覆蓋率 >= va_pct
def va_cover(res):
    inside = sum(v for lo, hi, v in res["profile"] if lo >= res["val"] - 1e-9 and hi <= res["vah"] + 1e-9)
    return inside / res["total_vol"] if res["total_vol"] else 0
H = [i + 1 for i in range(20)]; L = [i - 1 for i in range(20)]; C = list(range(20)); Vv = [100] * 20
r = V.vpvr(H, L, C, Vv, bins=20, va_pct=0.70)
check("VA 覆蓋率 >= 70%", va_cover(r) >= 0.70 - 1e-9)

# 4) 雙峰 → HVN 應至少抓到兩個高量節點
H = [11, 11, 31, 31]; L = [9, 9, 29, 29]; C = [10, 10, 30, 30]; Vv = [500, 500, 500, 500]
r = V.vpvr(H, L, C, Vv, bins=40)
check("雙峰 → HVN>=2", len(r["hvn"]) >= 2)

# 5) 契約：長度不一致 → ValueError；空輸入安全
try:
    V.vpvr([1, 2], [1], [1], [1]); _mm = False
except ValueError:
    _mm = True
check("長度不一致→ValueError", _mm)
r0 = V.vpvr([], [], [], [])
check("空輸入安全", r0["poc"] is None and r0["profile"] == [])

# 6) 不修改輸入
_H = [10, 12, 11]; _L = [9, 11, 10]; _C = [9.5, 11.5, 10.5]; _Vv = [100, 200, 150]
_snap = (list(_H), list(_L), list(_C), list(_Vv))
V.vpvr(_H, _L, _C, _Vv, bins=8)
check("不修改輸入", (_H, _L, _C, _Vv) == _snap)

# 7) summary_text 位置判讀
r = V.vpvr([101, 106, 96], [99, 104, 94], [100, 105, 95], [1000, 10, 10], bins=20)
check("現價>VAH→壓力判讀", "VAH" in V.summary_text(r, r["vah"] + 5))
check("現價<VAL→支撐判讀", "VAL" in V.summary_text(r, r["val"] - 5))

# 8) sr_zones：上方節點歸壓力、下方歸支撐、近→遠排序
r = V.vpvr([11, 21, 31, 41], [9, 19, 29, 39], [10, 20, 30, 40], [900, 100, 100, 800], bins=40)
z = V.sr_zones(r, price=25)
check("sr_zones: 壓力皆>現價", all(p > 25 for p, _ in z["resistance"]))
check("sr_zones: 支撐皆<現價", all(p < 25 for p, _ in z["support"]))
check("sr_zones: 壓力近→遠(遞增)", z["resistance"] == sorted(z["resistance"], key=lambda x: x[0]))
check("sr_zones: 支撐近→遠(遞減)", z["support"] == sorted(z["support"], key=lambda x: x[0], reverse=True))
check("sr_zones: 含 POC 標籤", any(k == "POC" for _, k in z["support"] + z["resistance"]))
z0 = V.sr_zones(V.vpvr([], [], [], []), price=10)
check("sr_zones: 空輸入安全", z0["support"] == [] and z0["resistance"] == [])
check("sr_zones: 無現價安全", V.sr_zones(r, None)["support"] == [])

# 9) suggest_bins：隨波動夾在 [20,60]，退化輸入安全
many = [100 + (i % 7) for i in range(50)]
b = V.suggest_bins([x + 2 for x in many], [x - 2 for x in many])
check("suggest_bins 介於 20~60", 20 <= b <= 60)
check("suggest_bins 空輸入回 24", V.suggest_bins([], []) == 24)
check("suggest_bins 全平回 1", V.suggest_bins([10, 10], [10, 10]) == 1)

print()
print("全部通過 ✅" if _fail == 0 else f"{_fail} 項失敗 ❌")
raise SystemExit(1 if _fail else 0)
