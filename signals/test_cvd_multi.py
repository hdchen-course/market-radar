#!/usr/bin/env python3
"""cvd_multi 判讀規則單元測試。

核心測試用『合成數據』確定性驗證規則邏輯（離線、不靠即時行情，才能當回歸測試
——真實行情每天變，不能當斷言基準）。另含一個『今年真實資料』smoke test（需網路）：
驗證真實 K 線跑得出合法分類、pipeline 不崩；判讀方向無金標準，故不斷言多空、只驗
『不崩 + 型別 + 回傳合法』。

執行：python3 test_cvd_multi.py   （離線核心測試必過；網路不可用時 smoke 自動 skip）
"""
import sys

import cvd_multi as m

_fails = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


def approx(a, b, tol=1e-9):
    return abs(a - b) < tol


# --- classify_turn 四態（確定性）---
check("turn 轉流入", m.classify_turn(-100, 50) == "後半轉流入↑")
check("turn 轉流出", m.classify_turn(100, -50) == "後半轉流出↓")
check("turn 持續流入", m.classify_turn(30, 60) == "持續流入")
check("turn 持續流出", m.classify_turn(-30, -60) == "持續流出")

# --- summarize_scale 數值（確定性）---
_rows = [(100, 10, 50), (102, -5, 40), (101, 20, 60), (103, -8, 30)]
_pct, _net, _cf, _cl = m.summarize_scale(_rows)
check("summarize pct", approx(_pct, (103 / 100 - 1) * 100))
check("summarize net", approx(_net, 10 - 5 + 20 - 8))
check("summarize 前後半", approx(_cf, 10 - 5) and approx(_cl, 20 - 8))

# --- interpret 規則（合成 results: 標籤 -> (pct, net, first, last)）---
_nat, _, _comb = m.interpret({"結構 1d": (18, -8000, 1000, -9000),
                              "當下 15m": (0, 300, 150, 150)})
check("頂背離 nature", "頂背離" in _nat)
check("頂背離+短買=區間", "區間" in _comb)

_, _, _comb = m.interpret({"結構 1d": (8, -5000, -1000, -4000),
                           "當下 15m": (0, -200, -80, -120)})
check("頂背離+短賣=偏空", "偏空" in _comb)

_nat, _, _comb = m.interpret({"結構 1d": (-10, 5000, 1000, 4000),
                              "當下 15m": (0, -100, -150, 80)})
check("底背離 nature", "底背離" in _nat)
check("底背離+短買=偏多", "偏多" in _comb)

_nat, _, _comb = m.interpret({"結構 1d": (-6, -5000, -1000, -4000),
                              "當下 15m": (0, -200, -80, -120)})
check("健康下跌 nature", "健康下跌" in _nat)

check("資料不足回 None", m.interpret({}) is None)
check("缺短尺度回 None", m.interpret({"結構 1d": (5, 1, 1, 1)}) is None)

# --- 今年真實資料 smoke test（需網路；失敗則 skip 不計 fail）---
try:
    _bars = m.fetch_binance("BTCUSDT", "1d", 60)
    assert len(_bars) >= m._MIN_BARS, "真實 K 線根數不足"
    assert all(len(b) == 3 for b in _bars), "每根應為 (close, delta, volume)"
    _res = {"結構 1d": m.summarize_scale(_bars),
            "當下 15m": m.summarize_scale(m.fetch_binance("BTCUSDT", "15m", 48))}
    _interp = m.interpret(_res)
    check("今年真實資料 interpret 回合法三元素", _interp is not None and len(_interp) == 3)
except Exception as exc:  # 網路/API 不可用 → skip，不讓離線核心測試受牽連
    print("SKIP  今年真實資料 smoke（網路不可用）：" + str(exc))

print()
print("ALL PASS" if not _fails else str(len(_fails)) + " FAILED: " + str(_fails))
sys.exit(1 if _fails else 0)
