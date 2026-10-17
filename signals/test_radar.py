#!/usr/bin/env python3
"""radar.scenario_engine 規則單元測試（合成 fixture、離線確定性）。

劇本引擎是純函數，用合成訊號斷言「給明確偏空/偏多輸入→輸出對應主劇本與理由」。
不碰網路，可當回歸測試。執行：python3 test_radar.py
"""
import sys

import radar

_fails = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


def st_all(direction):
    return {"1d": {"dir": direction}, "4h": {"dir": direction}, "1h": {"dir": direction}}


# --- 明確偏空：結構流出 + 短線流出 + 跌破VAL + funding熱 + 宏觀逆風 ---
bear_case = radar.scenario_engine(
    {"price": 100.0},
    {"結構 1d": (10, -5000, -1000, -4000), "當下 15m": (0, -200, -80, -120)},
    {"poc": 110.0, "vah": 115.0, "val": 105.0},
    st_all("空"),
    {"funding_pct": 0.02, "oi": 1},
    {"10Y": 5.3, "DXY": 103, "VIX": 25.0, "HY_OAS": 4.0, "HY_OAS_up": True},
)
check("偏空 verdict", "偏空" in bear_case["verdict"])
check("偏空 有多條空方理由", len(bear_case["bear"]) >= 2)
check("偏空 無多方理由", len(bear_case["bull"]) == 0)
check("watch 固定三項", len(bear_case["watch"]) == 3)

# --- 明確偏多：結構流入 + 短線流入 + 站上VAH + funding負 + ST多 + 宏觀無逆風 ---
bull_case = radar.scenario_engine(
    {"price": 120.0},
    {"結構 1d": (-8, 5000, 1000, 4000), "當下 15m": (0, 200, 80, 120)},
    {"poc": 110.0, "vah": 115.0, "val": 105.0},
    st_all("多"),
    {"funding_pct": -0.01, "oi": 1},
    {"10Y": 4.0, "DXY": 99, "VIX": 14.0, "HY_OAS": 3.0, "HY_OAS_up": False},
)
check("偏多 verdict", "偏多" in bull_case["verdict"])
check("偏多 有多條多方理由", len(bull_case["bull"]) >= 2)

# --- 區間/分歧：訊號相當，verdict 合法 + 面板欄位齊全 ---
mid_case = radar.scenario_engine(
    {"price": 108.0},
    {"結構 1d": (1, 100, 50, 50), "當下 15m": (0, 10, 5, 5)},
    {"poc": 110.0, "vah": 115.0, "val": 105.0},
    st_all("中"),
    {"funding_pct": 0.003, "oi": 1},
    {"10Y": 4.5, "DXY": 100, "VIX": 19.0, "HY_OAS": 3.1, "HY_OAS_up": False},
)
check("verdict 合法", ("偏多" in mid_case["verdict"]) or ("偏空" in mid_case["verdict"])
      or ("區間" in mid_case["verdict"]))
check("有 macro_note", bool(mid_case["macro_note"]))
check("VIX 警戒區進中性清單", any("警戒" in s[4] for s in mid_case["neutral"]))

# --- detect_candles 形態偵測（合成 OHLC fixture: (open,high,low,close)，確定性）---
def _pat(bars):
    return [p[0] for p in radar.detect_candles(bars)]


check("Hammer 錘子", "錘子線Hammer" in _pat([(10, 11, 9, 10), (9.7, 10.0, 8.0, 10.0)]))
check("ShootingStar 射擊之星", "射擊之星ShootingStar" in _pat([(10, 11, 9, 10), (10.0, 11.0, 10.0, 10.3)]))
check("Doji 十字星", "十字星Doji" in _pat([(10, 11, 9, 10), (10.0, 10.5, 9.5, 10.02)]))
check("BearishEngulfing 空頭吞沒", "空頭吞沒BearishEngulfing" in _pat([(10, 10.6, 9.9, 10.5), (10.6, 10.7, 9.9, 10.0)]))
check("BullishEngulfing 多頭吞沒", "多頭吞沒BullishEngulfing" in _pat([(10.5, 10.6, 9.4, 9.5), (9.4, 10.7, 9.3, 10.6)]))
check("不足兩根回空", radar.detect_candles([(10, 11, 9, 10)]) == [])

# candles 進得了 scenario（bias 歸類到 bull/bear/neutral 清單）
_sc = radar.scenario_engine(
    {"price": 100.0},
    {"結構 1d": (1, 100, 50, 50), "當下 15m": (0, 10, 5, 5)},
    {"poc": 110.0, "vah": 115.0, "val": 105.0},
    {"1d": {"dir": "中"}, "4h": {"dir": "中"}, "1h": {"dir": "中"}},
    {"funding_pct": 0.003, "oi": 1},
    {"10Y": 4.5, "DXY": 100, "VIX": 16.0, "HY_OAS": 3.1, "HY_OAS_up": False},
    candles=[("錘子線Hammer", "bull", "測試")],
)
check("K線形態進多方清單", any("錘子線Hammer" in s[4] for s in _sc["bull"]))

# --- build_prompt 產出給外部 LLM 的請求檔（含關鍵欄位）---
_prompt = radar.build_prompt(
    "TESTUSDT", False,
    {"price": 100.0, "pct": 1.0, "high": 101.0, "low": 99.0},
    {"poc": 110.0, "vah": 115.0, "val": 105.0},
    {"1d": {"dir": "中"}, "4h": {"dir": "中"}, "1h": {"dir": "中"}},
    {"funding_pct": 0.003, "oi": 1, "pctile": 48},
    {"10Y": 4.5, "DXY": 100, "VIX": 19.0, "HY_OAS": 3.1, "HY_OAS_up": False},
    [],
    mid_case,
)
check("prompt 含標的", "TESTUSDT" in _prompt)
check("prompt 含主劇本", "主劇本" in _prompt)
check("prompt 含情境催化任務", "情境催化" in _prompt)
check("prompt 含待盯數據", "待盯數據" in _prompt)

# --- build_html 產出貼進報告 6-C/6-D 的底稿欄片段 ---
_html = radar.build_html(
    "TESTUSDT", False,
    {"price": 100.0, "pct": 1.0, "high": 101.0, "low": 99.0},
    {"poc": 110.0, "vah": 115.0, "val": 105.0},
    {"1d": {"dir": "中"}, "4h": {"dir": "中"}, "1h": {"dir": "中"}},
    {"funding_pct": 0.003, "oi": 1, "pctile": 48},
    {"10Y": 4.5, "DXY": 100, "VIX": 19.0, "HY_OAS": 3.1, "HY_OAS_up": False},
    [],
    mid_case,
)
check("html 含 radar-draft 容器", 'class="radar-draft"' in _html)
check("html 含主劇本", "主劇本" in _html)
check("html 含 Value Area", "Value Area" in _html)
check("html 含未回測免責", "未回測" in _html)
check("html 偏多偏空區塊齊全", ("radar-bull" in _html) and ("radar-bear" in _html))

print()
print("ALL PASS" if not _fails else str(len(_fails)) + " FAILED: " + str(_fails))
sys.exit(1 if _fails else 0)
