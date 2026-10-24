"""test_patterns.py — patterns.py 全覆蓋單元測試（純標準庫、確定性、零相依）。
跑法：python3 test_patterns.py   （不需 venv）

涵蓋：
  A. 不變量/契約（定義無關）：型態數、值域、等長、空輸入、輸入驗證、不修改輸入、效能。
  B. 逐型態正向 fixture：全部 66 個 CDL* 各一個會觸發預期方向的合成 K 線。
  C. 易混淆對照：靠趨勢/落點區分者（hammer↔hangingman、三法方向、棄嬰孤島…）。
每個 fixture 的 OHLC 皆手工構造以滿足該型態定義；前綴 UP/DOWN 提供趨勢與平均實體基準。
"""
import time
import patterns as P

_fail = 0


def check(name, cond):
    global _fail
    print(("  ok  " if cond else "FAIL  ") + name)
    if not cond:
        _fail += 1


def sig(cdl, bars):
    o = [b[0] for b in bars]; h = [b[1] for b in bars]
    l = [b[2] for b in bars]; c = [b[3] for b in bars]
    return getattr(P, cdl)(o, h, l, c)[-1]


# 趨勢前綴：實體約 1.0（供 long_body>1.3 / short_body<0.5 與 trend() 判定）
DOWN = [(100 - i, 100 - i + 0.5, 100 - i - 1.5, 100 - i - 1) for i in range(12)]
UP = [(100 + i, 100 + i + 1.5, 100 + i - 0.5, 100 + i + 1) for i in range(12)]

# =========================================================================
print("== A. 不變量 ==")
_s = UP + DOWN
_o = [b[0] for b in _s]; _h = [b[1] for b in _s]; _l = [b[2] for b in _s]; _c = [b[3] for b in _s]
check("型態數 >= 64", P.pattern_count() >= 64)
check("FUNCS 數一致", len(P.FUNCS) == P.pattern_count())
_dom = _len = True
for nm in P.FUNCS:
    out = getattr(P, nm)(_o, _h, _l, _c)
    _len &= (len(out) == len(_c))
    _dom &= all(v in (-100, 0, 100) for v in out)
check("所有 CDL* 等長", _len)
check("所有 CDL* 值域 ⊂ {-100,0,100}", _dom)
check("空輸入安全", P.detect_last([]) == [] and P.scan([]) == {} and P.scan_all([]) == {})
check("單根不崩", P.CDLDOJI([10], [11], [9], [10.02]) == [100])
try:
    P.CDLDOJI([1, 2], [2], [0], [1]); _mm = False
except ValueError:
    _mm = True
check("長度不一致→ValueError", _mm)
_io = list(_o); P.scan(_s)
check("不修改輸入", _o == _io)
_t = time.time()
for _ in range(200):
    P.scan(_s)
_per = (time.time() - _t) / 200 * 1000
check(f"scan < 2ms/次（{_per:.3f}ms）", _per < 2.0)

# =========================================================================
print("== B. 逐型態正向（66）==")

# ---- 單根 ----
check("CDLDOJI", sig("CDLDOJI", UP + [(50, 51, 49, 50.02)]) == 100)
check("CDLDOJISTAR", sig("CDLDOJISTAR", UP + [(60, 63.05, 59.95, 63), (64, 64.1, 63.9, 64.02)]) == -100)
check("CDLDRAGONFLYDOJI", sig("CDLDRAGONFLYDOJI", UP + [(50, 50.05, 46, 50.0)]) == 100)
check("CDLGRAVESTONEDOJI", sig("CDLGRAVESTONEDOJI", UP + [(50, 54, 49.98, 50.0)]) == -100)
check("CDLLONGLEGGEDDOJI", sig("CDLLONGLEGGEDDOJI", UP + [(50, 53, 47, 50.1)]) == 100)
check("CDLRICKSHAWMAN", sig("CDLRICKSHAWMAN", UP + [(50, 53, 47, 50.05)]) == 100)
check("CDLHIGHWAVE", sig("CDLHIGHWAVE", UP + [(50, 51.35, 48.95, 50.3)]) == 100)
check("CDLSPINNINGTOP", sig("CDLSPINNINGTOP", UP + [(50, 52, 48, 50.5)]) == 100)
check("CDLMARUBOZU 多", sig("CDLMARUBOZU", UP + [(50, 53.05, 49.95, 53)]) == 100)
check("CDLMARUBOZU 空", sig("CDLMARUBOZU", UP + [(53, 53.05, 49.95, 50)]) == -100)
check("CDLCLOSINGMARUBOZU", sig("CDLCLOSINGMARUBOZU", UP + [(50, 53, 49.9, 53)]) == 100)
check("CDLLONGLINE", sig("CDLLONGLINE", UP + [(50, 53.2, 49.8, 53)]) == 100)
check("CDLSHORTLINE", sig("CDLSHORTLINE", UP + [(50, 50.3, 49.9, 50.25)]) == 100)
check("CDLBELTHOLD", sig("CDLBELTHOLD", UP + [(50, 53, 49.98, 52.9)]) == 100)
check("CDLHAMMER", sig("CDLHAMMER", DOWN + [(50, 50.1, 46, 49.3)]) == 100)
check("CDLINVERTEDHAMMER", sig("CDLINVERTEDHAMMER", DOWN + [(50, 54, 49.9, 50.7)]) == 100)
check("CDLHANGINGMAN", sig("CDLHANGINGMAN", UP + [(112, 112.1, 108, 111.3)]) == -100)
check("CDLSHOOTINGSTAR", sig("CDLSHOOTINGSTAR", UP + [(112, 116, 111.9, 112.7)]) == -100)
check("CDLTAKURI", sig("CDLTAKURI", UP + [(50, 50.03, 46, 50.0)]) == 100)

# ---- 雙根 ----
check("CDLENGULFING 多", sig("CDLENGULFING", [(10.5, 10.6, 9.4, 9.5), (9.4, 10.7, 9.3, 10.6)]) == 100)
check("CDLENGULFING 空", sig("CDLENGULFING", [(10, 10.6, 9.9, 10.5), (10.6, 10.7, 9.9, 10.0)]) == -100)
check("CDLHARAMI", sig("CDLHARAMI", DOWN + [(53, 53.1, 49.9, 50), (51, 51.4, 50.6, 51.2)]) == 100)
check("CDLHARAMICROSS", sig("CDLHARAMICROSS", DOWN + [(53, 53.1, 49.9, 50), (51, 51.1, 50.9, 51.01)]) == 100)
check("CDLPIERCING", sig("CDLPIERCING", DOWN + [(53, 53.1, 49.9, 50), (49.5, 51.9, 49.4, 51.8)]) == 100)
check("CDLDARKCLOUDCOVER", sig("CDLDARKCLOUDCOVER", UP + [(50, 53.1, 49.9, 53), (53.5, 53.6, 51.1, 51.2)]) == -100)
check("CDLHOMINGPIGEON", sig("CDLHOMINGPIGEON", DOWN + [(53, 53.1, 49.9, 50), (50.8, 50.9, 50.1, 50.3)]) == 100)
check("CDLMATCHINGLOW", sig("CDLMATCHINGLOW", DOWN + [(52, 52.1, 49.9, 50), (51, 51.1, 49.8, 50)]) == 100)
check("CDLONNECK", sig("CDLONNECK", DOWN + [(53, 53.1, 49.9, 50), (49.5, 50.0, 49.4, 49.9)]) == -100)
check("CDLINNECK", sig("CDLINNECK", DOWN + [(53, 53.1, 49.9, 50), (49.5, 50.2, 49.4, 50.05)]) == -100)
check("CDLTHRUSTING", sig("CDLTHRUSTING", DOWN + [(53, 53.1, 49.9, 50), (49.5, 51.5, 49.4, 51.0)]) == -100)
check("CDLSEPARATINGLINES", sig("CDLSEPARATINGLINES", UP + [(113, 113.1, 111.5, 111.8), (113, 116.1, 112.9, 116)]) == 100)
check("CDLKICKING", sig("CDLKICKING", UP + [(53, 53.05, 49.95, 50), (55, 58.05, 54.95, 58)]) == 100)
check("CDLKICKINGBYLENGTH", sig("CDLKICKINGBYLENGTH", UP + [(53, 53.05, 49.95, 50), (55, 57.05, 54.95, 57)]) == -100)
check("CDLCOUNTERATTACK", sig("CDLCOUNTERATTACK", DOWN + [(55, 55.1, 51.9, 52), (49, 52.1, 48.9, 52)]) == 100)
check("CDLTWEEZERTOP", sig("CDLTWEEZERTOP", UP + [(112, 113, 110, 111), (111.5, 113.0, 110.5, 112)]) == -100)
check("CDLTWEEZERBOTTOM", sig("CDLTWEEZERBOTTOM", DOWN + [(90, 91, 88, 89), (89.5, 91, 88.0, 90)]) == 100)
check("CDLRISINGWINDOW", sig("CDLRISINGWINDOW", UP + [(50, 51, 49, 50.5), (53, 54, 52, 53.5)]) == 100)
check("CDLFALLINGWINDOW", sig("CDLFALLINGWINDOW", DOWN + [(50, 51, 49, 49.5), (47, 48, 46, 47.5)]) == -100)
check("CDLMATCHINGHIGH", sig("CDLMATCHINGHIGH", UP + [(110, 111, 109.5, 110.8), (110.2, 111, 109.9, 110.8)]) == -100)

# ---- 三根 ----
check("CDLMORNINGSTAR", sig("CDLMORNINGSTAR", DOWN + [(55, 55.1, 51.9, 52), (51, 51.2, 50.7, 50.8), (51, 54.5, 50.9, 54)]) == 100)
check("CDLEVENINGSTAR", sig("CDLEVENINGSTAR", UP + [(50, 53.1, 49.9, 53), (53.5, 53.8, 53.2, 53.6), (53, 53.1, 49.4, 49.5)]) == -100)
check("CDLMORNINGDOJISTAR", sig("CDLMORNINGDOJISTAR", DOWN + [(55, 55.1, 51.9, 52), (51, 51.2, 50.8, 51.0), (51, 54.5, 50.9, 54)]) == 100)
check("CDLEVENINGDOJISTAR", sig("CDLEVENINGDOJISTAR", UP + [(50, 53.1, 49.9, 53), (53.5, 53.7, 53.3, 53.5), (53, 53.1, 49.4, 49.5)]) == -100)
check("CDLTRISTAR", sig("CDLTRISTAR", UP + [(50, 50.1, 49.9, 50.0), (48, 48.1, 47.9, 48.0), (50, 50.1, 49.9, 50.0)]) == 100)
check("CDL3WHITESOLDIERS", sig("CDL3WHITESOLDIERS",
      DOWN + [(50, 51.8, 49.9, 51.5), (51.0, 52.8, 50.9, 52.5), (52.0, 53.8, 51.9, 53.5)]) == 100)
check("CDL3BLACKCROWS", sig("CDL3BLACKCROWS",
      UP + [(53.5, 53.6, 51.7, 52.0), (52.5, 52.6, 50.7, 51.0), (51.5, 51.6, 49.7, 50.0)]) == -100)
check("CDLIDENTICAL3CROWS", sig("CDLIDENTICAL3CROWS",
      UP + [(55, 55.1, 51.9, 52), (52, 52.1, 48.9, 49), (49, 49.1, 45.9, 46)]) == -100)
check("CDL3INSIDE", sig("CDL3INSIDE", DOWN + [(53, 53.1, 49.9, 50), (51, 51.4, 50.6, 51.2), (51, 54, 50.9, 53.5)]) == 100)
check("CDL3OUTSIDE", sig("CDL3OUTSIDE", [(10, 10.6, 9.4, 9.5), (9.4, 10.7, 9.3, 10.6), (10.6, 11, 10.5, 10.9)]) == 100)
check("CDLADVANCEBLOCK", sig("CDLADVANCEBLOCK",
      UP + [(112, 114.6, 111.9, 114.5), (114, 115.6, 113.9, 115.4), (115, 116.2, 114.9, 115.6)]) == -100)
check("CDLSTALLEDPATTERN", sig("CDLSTALLEDPATTERN",
      UP + [(112, 115.1, 111.9, 115), (115, 118.1, 114.9, 118), (118, 118.6, 117.9, 118.3)]) == -100)
check("CDL2CROWS", sig("CDL2CROWS",
      UP + [(112, 115.1, 111.9, 115), (116.5, 116.6, 116.0, 116.1), (116.3, 116.4, 113.9, 114.5)]) == -100)
check("CDLUPSIDEGAP2CROWS", sig("CDLUPSIDEGAP2CROWS",
      UP + [(112, 115.1, 111.9, 115), (116.3, 116.6, 115.9, 116.0), (116.5, 116.7, 114.9, 115.5)]) == -100)
check("CDL3STARSINSOUTH", sig("CDL3STARSINSOUTH",
      DOWN + [(52, 52.1, 46, 50), (51, 51.1, 49, 49.5), (49.4, 49.41, 49.09, 49.1)]) == 100)
check("CDLUNIQUE3RIVER", sig("CDLUNIQUE3RIVER",
      DOWN + [(55, 55.1, 50, 50.5), (54, 54.2, 49, 51), (50, 50.6, 49.5, 50.3)]) == 100)
check("CDLTASUKIGAP", sig("CDLTASUKIGAP",
      UP + [(50, 51, 49.5, 51), (52, 53, 51.5, 53), (52.8, 52.9, 51.2, 51.5)]) == 100)
check("CDLSTICKSANDWICH", sig("CDLSTICKSANDWICH",
      DOWN + [(55, 55.1, 51.9, 52), (52.5, 54, 52.2, 53.5), (54, 54.1, 51.9, 52)]) == 100)
check("CDLHIKKAKE", sig("CDLHIKKAKE", [(50, 53, 48, 51), (50.5, 52, 49, 50), (49.5, 51.5, 47.5, 48)]) == 100)
check("CDLHIKKAKEMOD", sig("CDLHIKKAKEMOD",
      [(60, 61, 59, 60), (50, 53, 48, 51), (50.5, 52, 49, 50), (49.5, 51.5, 47.5, 48)]) == 100)

# ---- 四/五根 ----
check("CDL3LINESTRIKE", sig("CDL3LINESTRIKE",
      UP + [(50, 50.6, 49.9, 50.5), (50.6, 51.2, 50.5, 51.1), (51.2, 51.8, 51.1, 51.7), (52, 52.1, 49.5, 49.8)]) == 100)
check("CDLCONCEALBABYSWALL", sig("CDLCONCEALBABYSWALL",
      DOWN + [(55, 55.05, 51.95, 52), (52, 52.05, 48.95, 49), (48.5, 49.5, 47, 47.5), (48, 49.8, 45, 45.5)]) == 100)
check("CDLLADDERBOTTOM", sig("CDLLADDERBOTTOM",
      DOWN + [(58, 58.1, 54.9, 55), (56, 56.1, 52.9, 53), (54, 54.1, 50.9, 51), (52, 53, 49.9, 50.5), (53, 54, 52.5, 53.8)]) == 100)
check("CDLMATHOLD", sig("CDLMATHOLD",
      UP + [(50, 53.1, 49.9, 53), (54, 54.4, 53.6, 54.1), (54, 54.3, 53.5, 53.8), (53.9, 54.1, 53.3, 53.6), (53.7, 57.1, 53.5, 57)]) == 100)
check("CDLRISEFALL3METHODS", sig("CDLRISEFALL3METHODS",
      UP + [(50, 54.1, 49.9, 54), (53.5, 53.9, 52.5, 52.8), (53, 53.5, 52.2, 52.4), (52.6, 53.2, 51.9, 52.2), (52.5, 55.1, 52.3, 55)]) == 100)
check("CDLXSIDEGAP3METHODS", sig("CDLXSIDEGAP3METHODS",
      UP + [(50, 52, 49.8, 51.9), (53, 54, 52.5, 53.9), (53.5, 53.6, 51.0, 51.2)]) == 100)
check("CDLGAPSIDESIDEWHITE", sig("CDLGAPSIDESIDEWHITE",
      UP + [(50, 51, 49.8, 50.8), (52, 53, 51.8, 52.8), (52.1, 53.1, 51.9, 52.9)]) == 100)
check("CDLBREAKAWAY", sig("CDLBREAKAWAY",
      DOWN + [(60, 60.1, 56.9, 57), (55, 55.1, 53.9, 54), (54, 54.1, 52.9, 53), (53, 53.1, 51.9, 52), (52, 56, 51.9, 55.5)]) == 100)
check("CDLABANDONEDBABY", sig("CDLABANDONEDBABY",
      DOWN + [(55, 55.1, 51.9, 52), (50, 50.1, 49.9, 50.0), (51, 54.5, 50.5, 54)]) == 100)

# =========================================================================
print("== C. 易混淆對照 ==")
check("跌勢→HAMMER=+100", sig("CDLHAMMER", DOWN + [(50, 50.1, 46, 49.3)]) == 100)
check("漲勢同形→HAMMER=0", sig("CDLHAMMER", UP + [(112, 112.1, 108, 111.3)]) == 0)
check("漲勢→HANGINGMAN=-100", sig("CDLHANGINGMAN", UP + [(112, 112.1, 108, 111.3)]) == -100)
check("漲勢→SHOOTINGSTAR=-100", sig("CDLSHOOTINGSTAR", UP + [(112, 116, 111.9, 112.7)]) == -100)
check("跌勢同形→INVERTEDHAMMER=+100", sig("CDLINVERTEDHAMMER", DOWN + [(50, 54, 49.9, 50.7)]) == 100)
# 三線打擊方向=續勢（三白→+100，非反轉-100）
check("3LINESTRIKE 三白續勢=+100", sig("CDL3LINESTRIKE",
      UP + [(50, 50.6, 49.9, 50.5), (50.6, 51.2, 50.5, 51.1), (51.2, 51.8, 51.1, 51.7), (52, 52.1, 49.5, 49.8)]) == 100)
# gapsidesidewhite 下降分支=兩白（紅隊修正）
check("GAPSIDESIDEWHITE 下降=兩白→-100", sig("CDLGAPSIDESIDEWHITE",
      DOWN + [(50, 50.2, 49, 49.2), (47, 48, 46.8, 47.8), (47.1, 48.1, 46.9, 47.9)]) == -100)

print()
print("全部通過 ✅" if _fail == 0 else f"{_fail} 項失敗 ❌")
raise SystemExit(1 if _fail else 0)
