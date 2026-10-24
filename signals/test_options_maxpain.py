"""test_options_maxpain.py — options_maxpain 單元測試（純標準庫，離線 fixture + 不變量）。
跑法：cd signals && python3 test_options_maxpain.py
"""
import options_maxpain as om

_fail = 0


def ok(cond, msg):
    global _fail
    if cond:
        print(f"  PASS {msg}")
    else:
        _fail += 1
        print(f"  FAIL {msg}")


def R(expiry, cp, strike, oi, vol=0.0, gamma=0.0, delta=0.0):
    return {"expiry": expiry, "type": cp, "strike": strike,
            "oi": oi, "vol": vol, "gamma": gamma, "delta": delta}


print("== parse_occ ==")
ok(om.parse_occ("MSTR270115P00620000") == ("MSTR", "2027-01-15", "P", 620.0), "OCC put 2027-01-15 620")
ok(om.parse_occ("MSTR261023C00030000") == ("MSTR", "2026-10-23", "C", 30.0), "OCC call 30")
ok(om.parse_occ("AAPL260220C00250000")[3] == 250.0, "AAPL call strike 250")
ok(om.parse_occ("garbage") is None, "invalid -> None")
ok(om.parse_occ("") is None, "empty -> None")
ok(om.parse_occ("MSTR270115X00620000") is None, "bad type letter -> None")

print("== max_pain known-answer ==")
# call OI 集中低、put OI 集中高 → max pain 被 put 牆拉到高履約價
rows = [R("E", "C", 100, 1), R("C" and "E", "C", 120, 1),
        R("E", "P", 120, 100), R("E", "P", 100, 1)]
ok(om.max_pain(rows) == 120.0, "max pain pinned at heavy put strike 120")
# 對稱空倉
ok(om.max_pain([]) is None, "empty -> None")
ok(om.max_pain([R("E", "C", 100, 0), R("E", "P", 110, 0)]) is None, "all-zero OI -> None")
# 單側 call 牆把痛點拉低
rows2 = [R("E", "C", 50, 100), R("E", "C", 60, 1), R("E", "P", 60, 1)]
mp2 = om.max_pain(rows2)
ok(mp2 == 50.0, f"call-heavy pins low (got {mp2})")

print("== oi_walls ==")
w = om.oi_walls([R("E", "C", 400, 500), R("E", "C", 450, 900), R("E", "C", 500, 100),
                 R("E", "P", 300, 800), R("E", "P", 350, 1200)], top=2)
ok([s for s, _ in w["call"]] == [450, 400], "top2 call walls by OI order")
ok([s for s, _ in w["put"]] == [350, 300], "top2 put walls by OI order")
ok(all(v > 0 for _, v in w["call"]), "walls exclude zero OI")
w0 = om.oi_walls([R("E", "C", 400, 0)], top=3)
ok(w0["call"] == [] and w0["put"] == [], "all-zero -> empty walls")

print("== pcr ==")
pc = om.pcr([R("E", "C", 100, 10, vol=5), R("E", "P", 100, 20, vol=15)])
ok(abs(pc["oi"] - 2.0) < 1e-9, "PCR OI = 20/10 = 2.0")
ok(abs(pc["vol"] - 3.0) < 1e-9, "PCR Vol = 15/5 = 3.0")
pc2 = om.pcr([R("E", "P", 100, 20)])  # no calls
ok(pc2["oi"] is None, "no calls -> PCR OI None (no div0)")
ok(pc2["vol"] is None, "no call vol -> PCR Vol None")

print("== gex ==")
g = om.gex([R("E", "C", 100, 10, gamma=0.05), R("E", "P", 90, 10, gamma=0.01)], spot=100.0)
ok(g["net"] > 0, "call gamma dominates -> net positive")
ok(g["call_wall"][0] == 100, "call gamma wall at 100")
ok(g["put_wall"][0] == 90, "put gamma wall at 90")
g2 = om.gex([R("E", "P", 90, 1000, gamma=0.2)], spot=100.0)
ok(g2["net"] < 0, "put gamma dominates -> net negative")
ok(om.gex([], spot=None)["net"] == 0.0, "no spot -> zero net, no crash")
ok(om.gex([R("E", "C", 100, 10, gamma=0.05)], spot=0)["call_wall"] is None, "spot<=0 -> no walls")

print("== analyze + summary (empty & populated) ==")
res_empty = om.analyze(None, [], expiries=3)
ok(res_empty["near"]["max_pain_merged"] is None, "analyze empty -> merged max_pain None")
ok(res_empty["front_max_pain"] is None, "analyze empty -> front max_pain None")
ok("無資料" in om.summary_text(res_empty), "empty summary mentions 無資料")

rows_full = [
    R("2026-11-21", "C", 150, 2000, vol=100, gamma=0.03),
    R("2026-11-21", "C", 160, 3000, vol=50, gamma=0.02),
    R("2026-11-21", "P", 140, 2500, vol=80, gamma=0.025),
    R("2026-11-21", "P", 130, 1000, vol=20, gamma=0.015),
    R("2026-12-19", "C", 170, 500, vol=10, gamma=0.01),
    R("2026-12-19", "P", 120, 400, vol=5, gamma=0.01),
]
res = om.analyze(146.0, rows_full, expiries=3)
ok(len(res["expiries"]) == 2, "two expiries grouped")
ok(res["near"]["max_pain_merged"] is not None, "merged max_pain computed")
ok(res["front_max_pain"] == res["per_expiry"][0]["max_pain"], "front max_pain = nearest expiry's")
ok(res["front_expiry"] == "2026-11-21", "front expiry = nearest")
ok(res["per_expiry"][0]["expiry"] == "2026-11-21", "per-expiry sorted ascending")
txt = om.summary_text(res)
ok("Max Pain" in txt and "Call 牆" in txt and "PCR" in txt, "summary has key sections")
ok("最近到期" in txt and "合算" in txt, "summary distinguishes front vs merged")
ok(om.summary_html(res).startswith('<div class="opt-box">'), "html wrapper present")
# 不修改輸入
before = len(rows_full)
om.analyze(146.0, rows_full, 3)
ok(len(rows_full) == before, "analyze does not mutate input rows")

print("\nFAILS:", _fail)
raise SystemExit(1 if _fail else 0)
