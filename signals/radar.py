#!/usr/bin/env python3
"""盤面判讀引擎（規則化、可重複、可分享）。

給一個標的，整合多個客觀訊號，輸出：
  1. 客觀數據面板（報價 / 多尺度CVD / Volume Profile籌碼區 / SuperTrend三框 /
     funding-OI擁擠度 / 宏觀背景層）
  2. 解讀劇本（偏多 / 區間 / 偏空），每個附「為什麼這樣讀」（列出支持它的訊號）
  3. 需要盯哪些數據（多方/空方的確認與證偽訊號）

設計原則（誠實標註）：
  - 這是「規則引擎」＝客觀訊號的固定計分，輸出一致、可反覆跑、可分享。
  - 它『不』取代情境判讀：當天的新聞/政策催化（財報、指數調整、地緣）規則抓不到，
    那一層仍需人或 LLM 補。本引擎定位是「客觀儀表板 + 劇本骨架」。

資料來源：Binance（報價/K線/funding/OI，真 CVD）、Yahoo（宏觀殖利率/DXY/VIX）、
FRED（HY 信用利差，免費無需 key）。美股本尊無主動買賣分解→CVD 僅幣安（永續/鏡像）準確。

用法：
  python3 radar.py BTCUSDT
  python3 radar.py ETHUSDT --spot
  python3 radar.py NVDAUSDT          # 幣安美股鏡像（代表性打折）
依賴同目錄 cvd_multi.py。純標準庫、無需安裝套件。
"""
import argparse
import json
import sys
import urllib.request

import cvd_multi as cvd

# SuperTrend 參數（與每日報告一致）：ATR 週期、乘數、取樣根數。
_ST_PERIOD = 300
_ST_MULT = 3
_ST_LIMIT = 320
_ST_FRAMES = [("1d", "1d"), ("4h", "4h"), ("1h", "1h")]
# Volume Profile：價格分桶數（桶寬 = 區間 / 桶數）、Value Area 覆蓋比例。
_VP_BUCKETS = 50
_VP_VALUE_AREA = 0.70
_VP_LIMIT = 180
_VP_INTERVAL = "4h"
# funding 擁擠度門檻（/8h，%）：高於 hot = 多頭過熱、低於 0 = 空頭付費。
_FUNDING_HOT = 0.010
_FUNDING_NEG = 0.0
# 宏觀指標（對風險/無息資產：殖利率↑、美元↑、VIX↑、信用利差↑ 皆為逆風）。
_MACRO_YF = {"10Y": "%5ETNX", "DXY": "DX-Y.NYB", "VIX": "%5EVIX"}
_FRED_HY = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"
_UA = {"User-Agent": "Mozilla/5.0"}
_TIMEOUT = 20


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=_TIMEOUT)


# ---------- 各客觀訊號模組（盡量純函數，回傳結構化結果）----------

def fetch_ticker(symbol, use_spot):
    base = "https://api.binance.com/api/v3" if use_spot else "https://fapi.binance.com/fapi/v1"
    d = json.load(_get(f"{base}/ticker/24hr?symbol={symbol}"))
    return {"price": float(d["lastPrice"]), "pct": float(d["priceChangePercent"]),
            "high": float(d["highPrice"]), "low": float(d["lowPrice"])}


def volume_profile(symbol, use_spot):
    """回傳 {poc, vah, val}：成交量最大價位 + Value Area 上下緣（真實成交量）。"""
    bars = cvd.fetch_binance(symbol, _VP_INTERVAL, _VP_LIMIT, use_spot)
    # cvd.fetch_binance 回 (close, delta, vol)，用 close 當價位代表、vol 當量。
    prices_vols = [(close, vol) for close, _delta, vol in bars]
    lo = min(p for p, _ in prices_vols)
    hi = max(p for p, _ in prices_vols)
    width = (hi - lo) / _VP_BUCKETS or 1.0
    buckets = {}
    for price, vol in prices_vols:
        b = int((price - lo) // width)
        buckets[b] = buckets.get(b, 0.0) + vol
    total = sum(buckets.values())
    poc_bucket = max(buckets, key=buckets.get)
    poc = lo + (poc_bucket + 0.5) * width
    ordered = sorted(buckets, key=buckets.get, reverse=True)
    acc, chosen = 0.0, []
    for b in ordered:
        acc += buckets[b]
        chosen.append(b)
        if acc >= total * _VP_VALUE_AREA:
            break
    val = lo + min(chosen) * width
    vah = lo + (max(chosen) + 1) * width
    return {"poc": poc, "vah": vah, "val": val}


def _rma(values, period):
    avg = sum(values[:period]) / period
    out = [avg]
    for v in values[period:]:
        avg = (avg * (period - 1) + v) / period
        out.append(avg)
    return out


def supertrend_dir(symbol, interval, use_spot):
    """回傳該時間框架的 SuperTrend 方向：'多'/'空'/'中'（附帶收盤與上下軌）。"""
    base = "https://api.binance.com/api/v3" if use_spot else "https://fapi.binance.com/fapi/v1"
    k = json.load(_get(f"{base}/klines?symbol={symbol}&interval={interval}&limit={_ST_LIMIT}"))
    highs = [float(x[2]) for x in k]
    lows = [float(x[3]) for x in k]
    closes = [float(x[4]) for x in k]
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    atr = _rma(trs, _ST_PERIOD)[-1] if len(trs) > _ST_PERIOD else sum(trs) / len(trs)
    mid = (highs[-1] + lows[-1]) / 2
    upper = mid + _ST_MULT * atr
    lower = mid - _ST_MULT * atr
    close = closes[-1]
    direction = "多" if close > upper else ("空" if close < lower else "中")
    return {"dir": direction, "close": close, "upper": upper, "lower": lower}


def fetch_funding_oi(symbol):
    """加密永續的 funding/OI；現貨或鏡像取不到則回 None 欄位。"""
    try:
        prem = json.load(_get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"))
        oi = json.load(_get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"))
        return {"funding_pct": float(prem["lastFundingRate"]) * 100,
                "oi": float(oi["openInterest"])}
    except Exception:
        return {"funding_pct": None, "oi": None}


def _yahoo_last(sym):
    m = json.load(_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"))["chart"]["result"][0]["meta"]
    return m.get("regularMarketPrice")


def fetch_macro():
    """抓宏觀逆風指標（殖利率/美元/VIX/HY 信用利差）當背景層。"""
    out = {}
    for name, sym in _MACRO_YF.items():
        try:
            out[name] = _yahoo_last(sym)
        except Exception:
            out[name] = None
    try:
        rows = _get(_FRED_HY).read().decode().strip().splitlines()
        out["HY_OAS"] = float(rows[-1].split(",")[1])
        prev = float(rows[-2].split(",")[1])
        out["HY_OAS_up"] = out["HY_OAS"] > prev
    except Exception:
        out["HY_OAS"] = None
        out["HY_OAS_up"] = None
    return out


# ---------- 劇本引擎：把客觀訊號計分成 偏多/區間/偏空 + 理由 + 待盯 ----------

def scenario_engine(ticker, cvd_results, vp, st, funding_oi, macro):
    """回傳 dict：bull/bear 訊號清單（含理由）、主劇本、待盯數據。純函數、可測。"""
    bull, bear, neutral = [], [], []

    # 1. CVD 結構（1d）＋短線轉向
    interp = cvd.interpret(cvd_results)
    struct = cvd_results.get("結構 1d")
    if struct:
        if struct[1] < 0:
            bear.append(f"結構1d CVD 淨流出{struct[1]:+.0f}＝派發（價若漲為頂背離）")
        else:
            bull.append(f"結構1d CVD 淨流入{struct[1]:+.0f}＝吸籌")
    shortest = next((cvd_results[k] for k in cvd._SHORTEST_FIRST if k in cvd_results), None)
    if shortest:
        turn = cvd.classify_turn(shortest[2], shortest[3])
        (bull if turn in ("後半轉流入↑", "持續流入") else bear).append(f"短線CVD {turn}")

    # 2. SuperTrend 三框共振
    dirs = [s["dir"] for s in st.values()]
    if dirs.count("多") >= 2:
        bull.append(f"SuperTrend 三框偏多（{'/'.join(dirs)}）")
    elif dirs.count("空") >= 2:
        bear.append(f"SuperTrend 三框偏空（{'/'.join(dirs)}）")
    else:
        neutral.append(f"SuperTrend 三框分歧（{'/'.join(dirs)}）＝盤整")

    # 3. 價格相對 Volume Profile 位置
    price = ticker["price"]
    if price > vp["vah"]:
        bull.append(f"價 {price:.2f} 在 Value Area 上緣 {vp['vah']:.2f} 之上＝站上籌碼區")
    elif price < vp["val"]:
        bear.append(f"價 {price:.2f} 跌破 Value Area 下緣 {vp['val']:.2f}＝離開籌碼區下行")
    else:
        side = "POC之上" if price > vp["poc"] else "POC之下"
        neutral.append(f"價在 Value Area 內（{vp['val']:.2f}–{vp['vah']:.2f}）{side}＝區間")

    # 4. funding 擁擠度（反指：過熱易殺多、負值空頭擁擠可軋空）
    fr = funding_oi.get("funding_pct")
    if fr is not None:
        if fr >= _FUNDING_HOT:
            bear.append(f"funding {fr:.4f}% 偏熱＝多頭擁擠（易殺多）")
        elif fr < _FUNDING_NEG:
            bull.append(f"funding {fr:.4f}% 轉負＝空頭擁擠（軋空燃料）")
        else:
            neutral.append(f"funding {fr:.4f}% 中性＝無明顯擁擠")

    # 5. 宏觀背景層（對風險/無息資產：殖利率↑美元↑VIX↑HY↑＝逆風）
    tnx, dxy, vix = macro.get("10Y"), macro.get("DXY"), macro.get("VIX")
    hy_up = macro.get("HY_OAS_up")
    headwinds = []
    if vix is not None and vix >= 20:
        headwinds.append(f"VIX {vix:.1f}≥20 恐慌")
    elif vix is not None and vix >= 18:
        neutral.append(f"VIX {vix:.1f} 警戒區(18–20)，接近轉恐慌，需留意")
    if hy_up:
        headwinds.append(f"HY 信用利差走闊（{macro.get('HY_OAS')}）＝信用壓力升")
    macro_note = f"10Y {tnx} / DXY {dxy} / VIX {vix} / HY {macro.get('HY_OAS')}"
    if headwinds:
        bear.append("宏觀逆風：" + "、".join(headwinds))
    else:
        neutral.append(f"宏觀背景中性（{macro_note}）；需人工確認殖利率/美元當日方向")

    # 計分 → 主劇本
    bull_n, bear_n = len(bull), len(bear)
    if bull_n - bear_n >= 2:
        verdict = "偏多"
    elif bear_n - bull_n >= 2:
        verdict = "偏空"
    else:
        verdict = "區間/分歧（多空訊號相當，等長短同向）"

    # 待盯數據（確認/證偽）
    watch = [
        f"多方確認：短線CVD持續翻正 + 價站穩 POC {vp['poc']:.2f} / VAH {vp['vah']:.2f} + SuperTrend 轉多",
        f"空方確認：價跌破 VAL {vp['val']:.2f} + 結構CVD續流出 + funding 轉負 + 宏觀逆風(10Y↑/VIX破20/HY走闊)",
        "情境層（規則抓不到、需人工/LLM）：財報、指數調整(如MSCI)、政策/地緣催化、當日新聞",
    ]
    return {"bull": bull, "bear": bear, "neutral": neutral, "verdict": verdict,
            "cvd_interp": interp, "watch": watch, "macro_note": macro_note}


# ---------- 輸出 ----------

def build_cvd_results(symbol, use_spot):
    results = {}
    for label, interval, limit in cvd.BINANCE_TIMEFRAMES:
        try:
            bars = cvd.fetch_binance(symbol, interval, limit, use_spot)
            if len(bars) >= cvd._MIN_BARS:
                results[label] = cvd.summarize_scale(bars)
        except Exception:
            pass
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="盤面判讀引擎")
    parser.add_argument("symbol", help="標的代碼，如 BTCUSDT / ETHUSDT / NVDAUSDT")
    parser.add_argument("--spot", action="store_true", help="用幣安現貨（預設永續）")
    args = parser.parse_args(argv)
    sym, use_spot = args.symbol, args.spot

    ticker = fetch_ticker(sym, use_spot)
    cvd_results = build_cvd_results(sym, use_spot)
    vp = volume_profile(sym, use_spot)
    st = {label: supertrend_dir(sym, interval, use_spot) for label, interval in _ST_FRAMES}
    funding_oi = fetch_funding_oi(sym)
    macro = fetch_macro()
    sc = scenario_engine(ticker, cvd_results, vp, st, funding_oi, macro)

    print(f"===== {sym} 盤面判讀引擎（{'現貨' if use_spot else '永續'}）=====")
    print(f"[報價] {ticker['price']:.2f}  24h {ticker['pct']:+.2f}%  高{ticker['high']:.2f} 低{ticker['low']:.2f}")
    print(f"[籌碼區VP] POC {vp['poc']:.2f} | Value Area {vp['val']:.2f}–{vp['vah']:.2f}")
    st_str = " / ".join(f"{lbl}:{s['dir']}" for lbl, s in st.items())
    print(f"[SuperTrend({_ST_PERIOD},{_ST_MULT})] {st_str}")
    fr = funding_oi.get("funding_pct")
    print(f"[擁擠度] funding {('%.4f%%' % fr) if fr is not None else 'N/A(現貨/鏡像)'}  OI {funding_oi.get('oi')}")
    print(f"[宏觀背景] {sc['macro_note']}")
    if sc["cvd_interp"]:
        print(f"[CVD規則判讀] {' / '.join(sc['cvd_interp'])}")

    print(f"\n----- 解讀劇本（主劇本：{sc['verdict']}）-----")
    print("● 偏多劇本，為什麼：")
    for r in sc["bull"] or ["（無明顯多方訊號）"]:
        print(f"    + {r}")
    print("● 偏空劇本，為什麼：")
    for r in sc["bear"] or ["（無明顯空方訊號）"]:
        print(f"    - {r}")
    if sc["neutral"]:
        print("● 中性/區間訊號：")
        for r in sc["neutral"]:
            print(f"    · {r}")

    print("\n----- 需要盯哪些數據 -----")
    for w in sc["watch"]:
        print(f"    ☐ {w}")
    print("\n※ 本引擎為規則化客觀判讀，情境催化(財報/指數調整/地緣)需另行人工或 LLM 補。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
