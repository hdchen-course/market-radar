"""test_urpd.py — urpd（BTC 成本分布代理）單元測試。純標準庫、離線。
跑法：cd signals && python3 test_urpd.py
"""
import urpd

_fail = 0


def ok(cond, msg):
    global _fail
    if cond:
        print(f"  PASS {msg}")
    else:
        _fail += 1
        print(f"  FAIL {msg}")


print("== empty / degenerate ==")
e = urpd.urpd([], [], [], [])
ok(e["poc"] is None, "empty -> poc None")
ok(e["below_pct"] is None and e["above_pct"] is None, "empty -> no supply split")
ok("無資料" in urpd.summary_text(e), "empty summary safe")

flat = urpd.urpd([10, 10], [10, 10], [10, 10], [5, 5])
ok(flat["poc"] == 10, "flat price -> poc = that price")

print("== length mismatch (inherited from vpvr) ==")
try:
    urpd.urpd([1, 2], [1], [1, 2], [1, 2])
    ok(False, "mismatch should raise")
except ValueError:
    ok(True, "mismatch raises ValueError")

print("== supply split + clusters ==")
# 造一個量集中在低價帶的 profile，現價設在高檔 → above(套牢) 應小、below(獲利) 應大
H = [20, 21, 60, 61]
L = [18, 19, 58, 59]
C = [19, 20, 59, 60]
V = [1000, 1000, 10, 10]          # 絕大多數量在 ~20，少量在 ~60
res = urpd.urpd(H, L, C, V, bins=20)
ok(res["poc"] is not None and res["poc"] < 30, f"POC in low band (got {res['poc']})")
ok(abs((res["below_pct"] + res["above_pct"]) - 100.0) < 1e-6, "below+above = 100%")
ok(res["below_pct"] > res["above_pct"], "price high over low-cost cluster -> more supply below")
ok(res["poc_side"] == "above", "price above POC -> poc_side above (偏多結構)")
ok(isinstance(res["clusters"], list), "clusters is list")

print("== price override + poc_side below ==")
# 把現價指定在成本簇之下
res2 = urpd.urpd(H, L, C, V, bins=20, price=19.0)
ok(res2["price"] == 19.0, "price override honored")
ok(res2["poc_side"] in ("below", "at"), "low price -> poc_side below/at")
ok(res2["below_pct"] < res2["above_pct"], "low price -> more supply above (套牢)")

print("== summary content ==")
txt = urpd.summary_text(res)
ok("成本代理" in txt or "URPD" in txt, "summary flags proxy nature")
ok("POC" in txt, "summary has POC")
ok(urpd.summary_html(res).startswith('<div class="urpd-box">'), "html wrapper")

print("== log-bin mode ==")
rlog = urpd.urpd(H, L, C, V, bins=20, log=True)
ok(rlog["poc"] is not None and rlog["poc"] > 0, "log-bin POC positive (restored to linear price)")
ok(rlog["bin_width"] is None, "log-bin reports bin_width None (non-uniform in linear space)")
ok(all(x > 0 for x in rlog["clusters"]), "log-bin clusters restored to positive prices")
ok(abs((rlog["below_pct"] + rlog["above_pct"]) - 100.0) < 1e-6, "log-bin below+above = 100%")

print("== no input mutation ==")
Hc = list(H)
urpd.urpd(H, L, C, V, bins=20)
urpd.urpd(H, L, C, V, bins=20, log=True)
ok(H == Hc, "input list unchanged (incl. log mode)")

print("\nFAILS:", _fail)
raise SystemExit(1 if _fail else 0)
