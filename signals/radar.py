#!/usr/bin/env python3
"""盤面判讀引擎（規則化、可重複、可分享）。

給一個標的，整合多個客觀訊號，輸出：
  1. 客觀數據面板（報價 / 多尺度CVD / Volume Profile籌碼區 / SuperTrend三框 /
     funding-OI擁擠度(含歷史分位) / 宏觀背景層 / K線形態）
  2. 解讀劇本（偏多 / 區間 / 偏空 + 信心），每訊號附【強度★ × 維度權重】與「為什麼」
  3. 需要盯哪些數據（多方/空方的確認與證偽訊號）

判讀層設計（誠實標註）：
  - 不是等權 checklist：每個訊號有「方向 + 強度(0-3) + 維度權重」，加權計分定主劇本與信心。
  - 強度盡量用「數據自身的量」決定、而非瞎填門檻：funding 用近 120 期**歷史分位**、
    SuperTrend 用共振框數、Volume Profile 用價格離區間緣的距離、宏觀用逆風項數。
  - 條件交互：K線形態的多空意義 × 價格在籌碼區的位置（錘子在低檔才加權）；
    CVD 頂/底背離 × 價格位置。
  - ⚠ 維度權重(_DIM_WEIGHT)與判定門檻(_VERDICT_*)是**經驗值、未經回測**，會因市況/標的
    失準；本引擎是「加權儀表板」，**不**取代情境判讀（財報/指數調整/地緣/新聞仍需人或 LLM）。

資料來源：Binance（報價/K線/funding/OI，真 CVD）、Yahoo（殖利率/DXY/VIX）、FRED（HY 信用利差）。
用法：python3 radar.py BTCUSDT [--spot]；依賴同目錄 cvd_multi.py；純標準庫、無需安裝套件。
"""
import argparse
import datetime
import json
import sys
import urllib.request

import cvd_multi as cvd

# SuperTrend 參數（與每日報告一致）。
_ST_PERIOD = 300
_ST_MULT = 3
_ST_LIMIT = 320
_ST_FRAMES = [("1d", "1d"), ("4h", "4h"), ("1h", "1h")]
# Volume Profile。
_VP_BUCKETS = 50
_VP_VALUE_AREA = 0.70
_VP_LIMIT = 180
_VP_INTERVAL = "4h"
# funding 歷史分位。
_FUNDING_HIST_N = 120
_PCTILE_HOT = 80.0   # funding 分位 >= 此值 = 多頭過熱（偏空）
_PCTILE_COLD = 20.0  # funding 分位 <= 此值 = 多頭冷/偏空傾向；<0 值另判空頭擁擠
# K 線形態參數（公開標準 TA-Lib/Bulkowski）。
_DOJI_BODY_RATIO = 0.1
_SHADOW_BODY_MULT = 2.0
_MARUBOZU_RATIO = 0.9
# 宏觀。
_MACRO_YF = {"10Y": "%5ETNX", "DXY": "DX-Y.NYB", "VIX": "%5EVIX"}
_FRED_HY = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"
# ★判讀層：維度權重與主劇本門檻（經驗值、未回測）。
_DIM_WEIGHT = {"CVD結構": 1.5, "CVD短線": 1.0, "SuperTrend": 1.2,
               "VolumeProfile": 1.5, "funding": 1.0, "宏觀": 1.0, "K線形態": 0.5}
_VERDICT_HI = 4.0   # |加權分數差| >= 此值 = 高信心
_VERDICT_LO = 2.0   # >= 此值 = 低信心；否則 區間/分歧
_UA = {"User-Agent": "Mozilla/5.0"}
_TIMEOUT = 20


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=_TIMEOUT)


def _clamp_strength(x):
    """把連續強度壓到 0..3 整數。"""
    return max(0, min(3, int(round(x))))


def percentile_rank(values, x):
    """x 在 values 中的百分位(0-100)；values 非空。"""
    if not values:
        return 50.0
    below = sum(1 for v in values if v < x)
    return 100.0 * below / len(values)


# ---------- 客觀訊號模組 ----------

def fetch_ticker(symbol, use_spot):
    base = "https://api.binance.com/api/v3" if use_spot else "https://fapi.binance.com/fapi/v1"
    d = json.load(_get(f"{base}/ticker/24hr?symbol={symbol}"))
    return {"price": float(d["lastPrice"]), "pct": float(d["priceChangePercent"]),
            "high": float(d["highPrice"]), "low": float(d["lowPrice"])}


def volume_profile(symbol, use_spot):
    """回傳 {poc, vah, val}：成交量最大價位 + Value Area 上下緣（真實成交量）。"""
    bars = cvd.fetch_binance(symbol, _VP_INTERVAL, _VP_LIMIT, use_spot)
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
    return {"poc": poc, "vah": lo + (max(chosen) + 1) * width, "val": lo + min(chosen) * width}


def _rma(values, period):
    avg = sum(values[:period]) / period
    out = [avg]
    for v in values[period:]:
        avg = (avg * (period - 1) + v) / period
        out.append(avg)
    return out


def supertrend_dir(symbol, interval, use_spot):
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
    upper, lower, close = mid + _ST_MULT * atr, mid - _ST_MULT * atr, closes[-1]
    return {"dir": "多" if close > upper else ("空" if close < lower else "中")}


def fetch_funding(symbol):
    """回傳 {funding_pct, oi, pctile}；pctile 為當前 funding 在近 _FUNDING_HIST_N 期的百分位。"""
    out = {"funding_pct": None, "oi": None, "pctile": None}
    try:
        prem = json.load(_get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"))
        out["funding_pct"] = float(prem["lastFundingRate"]) * 100
        out["oi"] = float(json.load(_get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"))["openInterest"])
        hist = json.load(_get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit={_FUNDING_HIST_N}"))
        rates = [float(h["fundingRate"]) * 100 for h in hist]
        out["pctile"] = percentile_rank(rates, out["funding_pct"])
    except Exception:
        pass
    return out


def _yahoo_last(sym):
    m = json.load(_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"))["chart"]["result"][0]["meta"]
    return m.get("regularMarketPrice")


def fetch_macro():
    out = {}
    for name, sym in _MACRO_YF.items():
        try:
            out[name] = _yahoo_last(sym)
        except Exception:
            out[name] = None
    try:
        rows = _get(_FRED_HY).read().decode().strip().splitlines()
        out["HY_OAS"] = float(rows[-1].split(",")[1])
        out["HY_OAS_up"] = out["HY_OAS"] > float(rows[-2].split(",")[1])
    except Exception:
        out["HY_OAS"], out["HY_OAS_up"] = None, None
    return out


def fetch_ohlc(symbol, interval, limit, use_spot=False):
    base = "https://api.binance.com/api/v3" if use_spot else "https://fapi.binance.com/fapi/v1"
    k = json.load(_get(f"{base}/klines?symbol={symbol}&interval={interval}&limit={limit}"))
    return [(float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in k]


def detect_candles(bars):
    """偵測最後一根(吞沒看兩根)的 K 線形態，回傳 [(形態, bias, 說明)]。公開標準定義。"""
    if len(bars) < 2:
        return []
    o, h, l, c = bars[-1]
    po, _ph, _pl, pc = bars[-2]
    rng = (h - l) or 1e-9
    body, upper, lower = abs(c - o), h - max(o, c), min(o, c) - l
    out = []
    if body <= rng * _DOJI_BODY_RATIO:
        out.append(("十字星Doji", "neutral", "開收極近=多空猶豫、潛在變盤"))
    elif lower >= body * _SHADOW_BODY_MULT and upper <= body:
        out.append(("錘子線Hammer", "bull", "長下影=低檔有承接(需在下跌後才為反轉訊號)"))
    elif upper >= body * _SHADOW_BODY_MULT and lower <= body:
        out.append(("射擊之星ShootingStar", "bear", "長上影=高檔遭壓(需在上漲後才為反轉訊號)"))
    elif body >= rng * _MARUBOZU_RATIO:
        out.append(("大實體Marubozu", "bull" if c > o else "bear", "幾無影線=單邊強勢"))
    if c > o and pc < po and c >= po and o <= pc:
        out.append(("多頭吞沒BullishEngulfing", "bull", "今紅實體包住昨黑實體=買方反攻"))
    elif c < o and pc > po and o >= pc and c <= po:
        out.append(("空頭吞沒BearishEngulfing", "bear", "今黑實體包住昨紅實體=賣方反攻"))
    return out


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


# ---------- 劇本引擎：加權強度評分 + 分位 + 交互（純函數、可測）----------

def _price_zone(price, vp):
    """價格相對 Value Area 的位置：'above'/'below'/'upper_half'/'lower_half'。"""
    if price > vp["vah"]:
        return "above"
    if price < vp["val"]:
        return "below"
    return "upper_half" if price > vp["poc"] else "lower_half"


def scenario_engine(ticker, cvd_results, vp, st, funding, macro, candles=()):
    """回傳 dict：加權訊號清單(含強度) + 主劇本 + 信心 + 待盯 + cvd_interp。純函數。

    每個訊號 = (維度, 方向bull/bear/neutral, 強度0-3, 權重, 理由)。
    主劇本由 Σ(強度×權重) 的多空差決定；|差| 越大信心越高。
    """
    signals = []
    price = ticker["price"]
    zone = _price_zone(price, vp)

    def add(dim, direction, strength, reason):
        signals.append((dim, direction, _clamp_strength(strength), _DIM_WEIGHT.get(dim, 1.0), reason))

    # 1. CVD 結構(1d)：強度用「淨流出佔前後半規模」比例 + 與價格的背離
    struct = cvd_results.get("結構 1d")
    if struct:
        pct, net, cf, cl = struct
        scale = (abs(cf) + abs(cl)) or 1.0
        inten = 1 + 2 * min(1.0, abs(net) / scale)          # 1..3
        if net < 0:
            diverge = "，且價漲=頂背離" if pct > 0 else ""
            add("CVD結構", "bear", inten, f"結構1d CVD淨流出{net:+.0f}=派發{diverge}")
        else:
            diverge = "，且價跌=底背離" if pct < 0 else ""
            add("CVD結構", "bull", inten, f"結構1d CVD淨流入{net:+.0f}=吸籌{diverge}")

    # 2. CVD 短線轉向
    shortest = next((cvd_results[k] for k in cvd._SHORTEST_FIRST if k in cvd_results), None)
    if shortest:
        turn = cvd.classify_turn(shortest[2], shortest[3])
        buy = turn in ("後半轉流入↑", "持續流入")
        add("CVD短線", "bull" if buy else "bear", 2 if "轉" in turn else 1, f"短線CVD {turn}")

    # 3. SuperTrend 共振：強度=同向框數
    dirs = [s["dir"] for s in st.values()]
    if dirs.count("多") >= 2:
        add("SuperTrend", "bull", dirs.count("多"), f"三框偏多（{'/'.join(dirs)}）")
    elif dirs.count("空") >= 2:
        add("SuperTrend", "bear", dirs.count("空"), f"三框偏空（{'/'.join(dirs)}）")
    else:
        add("SuperTrend", "neutral", 1, f"三框分歧（{'/'.join(dirs)}）=盤整")

    # 4. Volume Profile 位置：強度用離區間緣的距離（相對 VA 寬度）
    va_width = (vp["vah"] - vp["val"]) or 1.0
    if zone == "above":
        add("VolumeProfile", "bull", 1 + 3 * (price - vp["vah"]) / va_width,
            f"價 {price:.2f} 站上 Value Area 上緣 {vp['vah']:.2f}=突破籌碼區")
    elif zone == "below":
        add("VolumeProfile", "bear", 1 + 3 * (vp["val"] - price) / va_width,
            f"價 {price:.2f} 跌破 Value Area 下緣 {vp['val']:.2f}=離開籌碼區下行")
    else:
        add("VolumeProfile", "neutral", 1,
            f"價在 Value Area 內（{vp['val']:.2f}–{vp['vah']:.2f}，{'POC上' if zone=='upper_half' else 'POC下'}）=區間")

    # 5. funding 擁擠度：用歷史分位（相對自己、非固定門檻）
    fr, pctile = funding.get("funding_pct"), funding.get("pctile")
    if fr is not None and pctile is not None:
        if fr < 0:
            add("funding", "bull", 3, f"funding {fr:.4f}%<0=空頭付費擁擠（軋空燃料，分位{pctile:.0f}%）")
        elif pctile >= _PCTILE_HOT:
            add("funding", "bear", 1 + 2 * (pctile - _PCTILE_HOT) / (100 - _PCTILE_HOT),
                f"funding {fr:.4f}% 近120期分位{pctile:.0f}%=多頭偏熱（易殺多）")
        elif pctile <= _PCTILE_COLD:
            add("funding", "neutral", 1, f"funding {fr:.4f}% 分位{pctile:.0f}%=多頭熱度低（偏冷、非空頭擁擠）")
        else:
            add("funding", "neutral", 1, f"funding {fr:.4f}% 分位{pctile:.0f}%=中性")

    # 6. 宏觀背景：逆風項數當強度（對風險/無息資產）
    tnx, dxy, vix = macro.get("10Y"), macro.get("DXY"), macro.get("VIX")
    heads = []
    if vix is not None and vix >= 20:
        heads.append(f"VIX {vix:.1f}≥20 恐慌")
    elif vix is not None and vix >= 18:
        add("宏觀", "neutral", 1, f"VIX {vix:.1f} 警戒區(18-20)")
    if macro.get("HY_OAS_up"):
        heads.append(f"HY 信用利差走闊({macro.get('HY_OAS')})")
    macro_note = f"10Y {tnx} / DXY {dxy} / VIX {vix} / HY {macro.get('HY_OAS')}"
    if heads:
        add("宏觀", "bear", len(heads) + 1, "宏觀逆風：" + "、".join(heads))

    # 7. K 線形態 × 位置交互：錘子在低檔/射擊之星在高檔才加權，反之弱化
    for name, bias, note in candles:
        strength = 1.0
        loc = ""
        if bias == "bull":
            strength = 2.0 if zone in ("below", "lower_half") else 0.5
            loc = "（在籌碼區低檔，反轉意義強）" if strength > 1 else "（非低檔，弱化）"
        elif bias == "bear":
            strength = 2.0 if zone in ("above", "upper_half") else 0.5
            loc = "（在籌碼區高檔，反轉意義強）" if strength > 1 else "（非高檔，弱化）"
        add("K線形態", bias, strength, f"K線 {name}：{note}{loc}")

    # 加權計分
    bull = [s for s in signals if s[1] == "bull"]
    bear = [s for s in signals if s[1] == "bear"]
    neutral = [s for s in signals if s[1] == "neutral"]
    bull_score = sum(s[2] * s[3] for s in bull)
    bear_score = sum(s[2] * s[3] for s in bear)
    diff = bull_score - bear_score
    if diff >= _VERDICT_HI:
        verdict = f"偏多（高信心，加權分 {bull_score:.1f} vs {bear_score:.1f}）"
    elif diff >= _VERDICT_LO:
        verdict = f"偏多（低信心，{bull_score:.1f} vs {bear_score:.1f}）"
    elif diff <= -_VERDICT_HI:
        verdict = f"偏空（高信心，{bull_score:.1f} vs {bear_score:.1f}）"
    elif diff <= -_VERDICT_LO:
        verdict = f"偏空（低信心，{bull_score:.1f} vs {bear_score:.1f}）"
    else:
        verdict = f"區間/分歧（多空加權相當 {bull_score:.1f} vs {bear_score:.1f}，等長短同向）"

    watch = [
        f"多方確認：短線CVD持續翻正 + 價站穩 POC {vp['poc']:.2f} / VAH {vp['vah']:.2f} + SuperTrend 轉多",
        f"空方確認：價跌破 VAL {vp['val']:.2f} + 結構CVD續流出 + funding 轉負 + 宏觀逆風(VIX破20/HY走闊)",
        "情境層（規則抓不到、需人工/LLM）：財報、指數調整(如MSCI)、政策/地緣催化、當日新聞",
    ]
    return {"bull": bull, "bear": bear, "neutral": neutral, "verdict": verdict,
            "bull_score": bull_score, "bear_score": bear_score,
            "cvd_interp": cvd.interpret(cvd_results), "macro_note": macro_note, "watch": watch}


# ---------- 輸出 ----------

def build_prompt(sym, use_spot, ticker, vp, st, funding, macro, candles, sc):
    """產生給外部免費 LLM(ChatGPT/Gemini/Grok)交叉判讀的請求檔(markdown)。

    radar 是 local 客觀規則層，把『情境判讀』外包給雲端 LLM(免費)：
    `python3 radar.py BTCUSDT --prompt > req.md` → 貼給免費 LLM 補當日催化+權衡。
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    fr, pct = funding.get("funding_pct"), funding.get("pctile")
    fund_s = f"{fr:.4f}% (近120期分位{pct:.0f}%)" if (fr is not None and pct is not None) else "N/A(現貨/鏡像)"
    st_s = " / ".join(f"{k}:{v['dir']}" for k, v in st.items())
    cand_s = "、".join(f"{n}({b})" for n, b, _ in candles) or "無明顯形態"
    cvd_s = " / ".join(sc["cvd_interp"]) if sc["cvd_interp"] else "N/A"

    def sig_lines(sigs):
        return "\n".join(f"  - [強度{s[2]}/3 ×權重{s[3]}] {s[0]}：{s[4]}" for s in sigs) or "  -（無）"

    watch_s = "\n".join("- " + w for w in sc["watch"])
    return (
        f"# {sym} 盤面判讀請求（{'現貨' if use_spot else '永續'}，{now}）\n\n"
        "## 給你（免費 LLM）的任務\n"
        "以下是 local 規則引擎 radar.py 的**客觀數據與初判**，它**抓不到當日新聞/催化**。請你：\n"
        f"1. 查/補今天 {sym} 的**情境催化**（財報、指數調整如 MSCI、政策/地緣、鏈上或產業大事）——規則層盲區。\n"
        "2. 結合客觀數據，給**偏多/區間/偏空三劇本的機率與觸發條件**。\n"
        "3. 指出規則初判**可能被當日情境推翻**之處。\n"
        "4. 一句可執行結論 + 風控（停損/部位）。\n\n"
        "## 客觀面板（radar.py 規則層）\n"
        f"- 報價：{ticker['price']:.4f}　24h {ticker['pct']:+.2f}%　高 {ticker['high']:.4f} 低 {ticker['low']:.4f}\n"
        f"- Volume Profile 籌碼區：POC {vp['poc']:.2f}｜Value Area {vp['val']:.2f}–{vp['vah']:.2f}\n"
        f"- SuperTrend({_ST_PERIOD},{_ST_MULT})：{st_s}\n"
        f"- funding 擁擠度：{fund_s}｜OI {funding.get('oi')}\n"
        f"- 宏觀背景：{sc['macro_note']}\n"
        f"- K 線形態(日)：{cand_s}\n"
        f"- CVD 規則判讀：{cvd_s}\n\n"
        "## 規則初判（加權強度；權重/門檻為經驗值、未回測）\n"
        f"**主劇本：{sc['verdict']}**\n"
        f"偏多訊號：\n{sig_lines(sc['bull'])}\n"
        f"偏空訊號：\n{sig_lines(sc['bear'])}\n"
        f"中性/區間：\n{sig_lines(sc['neutral'])}\n\n"
        f"## 待盯數據\n{watch_s}\n\n"
        "## 限制聲明\n"
        "規則層不含情境催化、權重未回測、K線單根須配合位置。請以你查到的當日新聞/財報/事件為準，"
        "修正或推翻上面的規則初判。\n"
    )


def build_html(sym, use_spot, ticker, vp, st, funding, macro, candles, sc):
    """產生可直接貼進 /dailyecreport 報告 6-C/6-D『🛰️ radar 客觀底稿欄』的 HTML 片段。

    把 radar 客觀規則層的面板＋主劇本＋多空理由＋待盯，整理成自包含 div，
    用法：`python3 radar.py BTCUSDT --html`，輸出貼到報告對應資產段，省去手抄。
    內文用全形標點（與報告一致）。情境催化(財報/MSCI/地緣)仍須人工補、不在此欄。
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    fr, pct = funding.get("funding_pct"), funding.get("pctile")
    fund_s = (f"{fr:.4f}%（近120期分位{pct:.0f}%）" if (fr is not None and pct is not None)
              else "N/A（現貨/鏡像）")
    st_s = " / ".join(f"{k}:{v['dir']}" for k, v in st.items())
    cand_s = "、".join(f"{n}（{b}）" for n, b, _ in candles) or "無明顯形態"
    cvd_s = " / ".join(sc["cvd_interp"]) if sc["cvd_interp"] else "N/A"

    def li(sigs):
        rows = "".join(
            f"<li>[強度{s[2]}/3 ×權重{s[3]}] {s[0]}：{s[4]}</li>" for s in sigs)
        return rows or "<li>（無）</li>"

    watch = "".join(f"<li>{w}</li>" for w in sc["watch"])
    kind = "現貨" if use_spot else "永續"
    return (
        f'<div class="radar-draft">\n'
        f'  <div class="radar-head">🛰️ radar 客觀底稿（{sym}，{kind}，{now}）'
        f'｜主劇本：{sc["verdict"]}</div>\n'
        f'  <table class="radar-panel">\n'
        f'    <tr><td>報價</td><td>{ticker["price"]:.4f}　24h {ticker["pct"]:+.2f}%</td></tr>\n'
        f'    <tr><td>Volume Profile</td><td>POC {vp["poc"]:.2f}｜Value Area '
        f'{vp["val"]:.2f}–{vp["vah"]:.2f}</td></tr>\n'
        f'    <tr><td>SuperTrend({_ST_PERIOD},{_ST_MULT})</td><td>{st_s}</td></tr>\n'
        f'    <tr><td>funding/OI</td><td>{fund_s}｜OI {funding.get("oi")}</td></tr>\n'
        f'    <tr><td>宏觀背景</td><td>{sc["macro_note"]}</td></tr>\n'
        f'    <tr><td>K線形態(日)</td><td>{cand_s}</td></tr>\n'
        f'    <tr><td>CVD規則判讀</td><td>{cvd_s}</td></tr>\n'
        f'  </table>\n'
        f'  <div class="radar-bull"><b>偏多訊號：</b><ul>{li(sc["bull"])}</ul></div>\n'
        f'  <div class="radar-bear"><b>偏空訊號：</b><ul>{li(sc["bear"])}</ul></div>\n'
        f'  <div class="radar-watch"><b>待盯數據：</b><ul>{watch}</ul></div>\n'
        f'  <div class="radar-note">※ radar 為規則化客觀層，權重/門檻為經驗值未回測；'
        f'情境催化（財報/MSCI 指數調整/地緣/當日新聞）不在此欄，須人工或 LLM 補，'
        f'與我的情境判讀衝突時兩者並陳。</div>\n'
        f'</div>\n'
    )


def _fmt_signal(sig):
    dim, direction, strength, weight, reason = sig
    stars = "★" * strength + "☆" * (3 - strength)
    return f"    [{stars} ×w{weight}] {dim}：{reason}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="盤面判讀引擎（加權強度版）")
    parser.add_argument("symbol", help="標的代碼，如 BTCUSDT / ETHUSDT / NVDAUSDT")
    parser.add_argument("--spot", action="store_true", help="用幣安現貨（預設永續）")
    parser.add_argument("--prompt", action="store_true",
                        help="輸出給外部免費 LLM(ChatGPT/Gemini/Grok)交叉判讀的請求檔(markdown)")
    parser.add_argument("--html", action="store_true",
                        help="輸出可貼進 /dailyecreport 報告 6-C/6-D 的 radar 客觀底稿欄 HTML 片段")
    args = parser.parse_args(argv)
    sym, use_spot = args.symbol, args.spot

    ticker = fetch_ticker(sym, use_spot)
    cvd_results = build_cvd_results(sym, use_spot)
    vp = volume_profile(sym, use_spot)
    st = {label: supertrend_dir(sym, interval, use_spot) for label, interval in _ST_FRAMES}
    funding = fetch_funding(sym)
    macro = fetch_macro()
    candles = detect_candles(fetch_ohlc(sym, "1d", 3, use_spot))
    sc = scenario_engine(ticker, cvd_results, vp, st, funding, macro, candles)

    if args.prompt:
        print(build_prompt(sym, use_spot, ticker, vp, st, funding, macro, candles, sc))
        return 0
    if args.html:
        print(build_html(sym, use_spot, ticker, vp, st, funding, macro, candles, sc))
        return 0

    print(f"===== {sym} 盤面判讀引擎（加權強度版，{'現貨' if use_spot else '永續'}）=====")
    print(f"[報價] {ticker['price']:.2f}  24h {ticker['pct']:+.2f}%  高{ticker['high']:.2f} 低{ticker['low']:.2f}")
    print(f"[籌碼區VP] POC {vp['poc']:.2f} | Value Area {vp['val']:.2f}–{vp['vah']:.2f}")
    print(f"[SuperTrend({_ST_PERIOD},{_ST_MULT})] " + " / ".join(f"{k}:{v['dir']}" for k, v in st.items()))
    fr, pct = funding.get("funding_pct"), funding.get("pctile")
    print(f"[擁擠度] funding {('%.4f%% (近120期分位%.0f%%)' % (fr, pct)) if fr is not None and pct is not None else 'N/A(現貨/鏡像)'}  OI {funding.get('oi')}")
    print(f"[宏觀背景] {sc['macro_note']}")
    print(f"[K線形態(日)] " + ("、".join(f"{n}({b})" for n, b, _ in candles) or "無明顯形態"))
    if sc["cvd_interp"]:
        print(f"[CVD規則判讀] {' / '.join(sc['cvd_interp'])}")

    print(f"\n----- 解讀劇本（主劇本：{sc['verdict']}）-----")
    print("● 偏多劇本（強度★×權重）：")
    for s in sorted(sc["bull"], key=lambda x: -x[2] * x[3]) or []:
        print(_fmt_signal(s))
    if not sc["bull"]:
        print("    （無多方訊號）")
    print("● 偏空劇本（強度★×權重）：")
    for s in sorted(sc["bear"], key=lambda x: -x[2] * x[3]) or []:
        print(_fmt_signal(s))
    if not sc["bear"]:
        print("    （無空方訊號）")
    if sc["neutral"]:
        print("● 中性/區間：")
        for s in sc["neutral"]:
            print(_fmt_signal(s))

    print("\n----- 需要盯哪些數據 -----")
    for w in sc["watch"]:
        print(f"    ☐ {w}")
    print("\n※ 權重/門檻為經驗值未回測；本引擎為加權客觀儀表板，情境催化(財報/指數調整/地緣)需人工或 LLM 補。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
