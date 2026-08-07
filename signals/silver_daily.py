#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
白銀(XAG)每日傾向工具 — 抓當日免費數據,比對 rulebook.json,輸出綜合傾向。

用法:
    /tmp/silvenv/bin/python signals/silver_daily.py
    (需 yfinance + pandas;/tmp/silvenv 已具備)

設計原則(團隊研究定案):
  - 回測已完成,本工具不重跑回測,只抓今日數據比對凍結的規則書。
  - 全部輸入用免費、T-0 可得的 yfinance(SI=F/GC=F/^VIX/CL=F) + CFTC 免費 API。
  - 誠實:當沒有可用訊號觸發,就輸出「觀望」,不硬湊方向。
  - 中性雙向,但結構上偏空側訊號幾乎全失效(見 rulebook.composite.structural_limit)。
"""
import json, os, sys, urllib.request, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RULEBOOK = os.path.join(HERE, "rulebook.json")

# ---------- 資料抓取(全免費) ----------
def fetch_yf(symbol, days=420):
    """yfinance chart API,免 key。回傳 date->close 的 Series。"""
    import time
    p2 = int(time.time()); p1 = p2 - days * 86400
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    r = d["chart"]["result"][0]
    ts = r["timestamp"]; cl = r["indicators"]["quote"][0]["close"]
    s = pd.Series({pd.Timestamp(t, unit="s").normalize(): c
                   for t, c in zip(ts, cl) if c is not None}).sort_index()
    return s

def fetch_cot():
    """CFTC 白銀 COT(免費、免 key)。回傳最新一週的 net、52週百分位。"""
    base = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    # 抓 300 週以支撐 5 年(260週)分位計算
    q = {"$limit": "300",
         "$order": "report_date_as_yyyy_mm_dd DESC",
         "$select": ("report_date_as_yyyy_mm_dd,open_interest_all,"
                     "noncomm_positions_long_all,noncomm_positions_short_all"),
         "$where": "cftc_contract_market_code='084691'"}
    url = base + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    rows = json.load(urllib.request.urlopen(req, timeout=60))
    df = pd.DataFrame(rows)
    for c in ["noncomm_positions_long_all", "noncomm_positions_short_all", "open_interest_all"]:
        df[c] = pd.to_numeric(df[c])
    df["net"] = df.noncomm_positions_long_all - df.noncomm_positions_short_all
    df = df.iloc[::-1].reset_index(drop=True)  # 轉回時間正序

    def strict_pct(s, w):
        """strict 百分位:當前值 > 過去(w-1)週的比例,與現有算法一致。"""
        win = s.iloc[-w:] if len(s) >= w else s
        return (win.iloc[-1] > win.iloc[:-1]).mean() * 100 if len(win) > 1 else float("nan")

    net = df.net
    latest = net.iloc[-1]
    short = df.noncomm_positions_short_all
    short_now = int(short.iloc[-1])
    oi_now = int(df.open_interest_all.iloc[-1])
    # 26 週全距(reviewer2 要求:附帶寬,否則 92% 看起來很有力但其實是窄帶排序)
    win26 = short.iloc[-26:] if len(short) >= 26 else short
    short_range26 = int(win26.max() - win26.min())

    return {
        "net": int(latest),
        "pct52": round(strict_pct(net, 52), 1),
        "net4": int(latest - net.iloc[-5]) if len(net) >= 5 else None,
        "date": df.report_date_as_yyyy_mm_dd.iloc[-1][:10],
        # --- 空頭顯示層(reviewer2 定版:雙尺度 + 絕對口數 + 全距,皆非進場訊號) ---
        "short": short_now,
        "short_pct26": round(strict_pct(short, 26), 1),   # 近半年
        "short_pct52": round(strict_pct(short, 52), 1),   # 一年
        "short_pct260": round(strict_pct(short, 260), 1), # 5年(受OI時代漂移影響,不可跨代硬比)
        "short_net4": int(short.iloc[-1] - short.iloc[-5]) if len(short) >= 5 else None,
        "short_oi_pct": round(short_now / oi_now * 100, 1) if oi_now else None,
        "short_range26": short_range26,
        "oi": oi_now,
    }

# ---------- 指標計算 ----------
def pct_change_nd(s, n):
    return (s.iloc[-1] / s.iloc[-1 - n] - 1) * 100 if len(s) > n else float("nan")

def compute(rb):
    si = fetch_yf("SI=F"); gc = fetch_yf("GC=F")
    vix = fetch_yf("^VIX"); cl = fetch_yf("CL=F")
    # 對齊金銀到同一交易日
    idx = si.index.intersection(gc.index)
    si_a, gc_a = si.reindex(idx).ffill(), gc.reindex(idx).ffill()
    gsr = gc_a / si_a
    gsr_z = (gsr.iloc[-1] - gsr.tail(250).mean()) / gsr.tail(250).std() if len(gsr) >= 250 else float("nan")
    m = {
        "silver": round(si.iloc[-1], 2),
        "silver_date": str(si.index[-1].date()),
        "gold": round(gc.iloc[-1], 2),
        "gsr": round(gsr.iloc[-1], 2),
        "gsr_5d_chg": round(gsr.iloc[-1] - gsr.iloc[-6], 2) if len(gsr) > 5 else float("nan"),
        "gsr_20d_chg": round(gsr.iloc[-1] - gsr.iloc[-21], 2) if len(gsr) > 20 else float("nan"),
        "gsr_z250": round(gsr_z, 2),
        "vix": round(vix.iloc[-1], 2),
        "oil_20d_pct": round(pct_change_nd(cl, 20), 1),
        "ma200": round(si.rolling(200).mean().iloc[-1], 2) if len(si) >= 200 else float("nan"),
        "low20": round(si.tail(20).min(), 2),
    }
    try:
        m["cot"] = fetch_cot()
    except Exception as e:
        m["cot"] = {"error": str(e)}
    return m

# ---------- 訊號比對 ----------
def evaluate(rb, m):
    fired = []           # 觸發的進場訊號
    lights = []          # 環境燈/背景色
    gsr = m["gsr"]; gsr5 = m["gsr_5d_chg"]; gsr20 = m["gsr_20d_chg"]
    oil20 = m["oil_20d_pct"]; vix = m["vix"]; gz = m["gsr_z250"]

    # --- 進場訊號 ---
    for s in rb["signals"]:
        if s["key"] == "S3H":
            ok = (gsr5 >= 2) and (gsr > 81.6)
        elif s["key"] == "S3":
            ok = (gsr5 >= 2)
        else:
            ok = False
        if ok:
            fired.append({**s, "signed_weight": s["weight"] if s["dir"] == "多" else -s["weight"]})

    # --- 環境燈 / 背景色 ---
    def light(key, cond, bias, w):
        if cond:
            lights.append({"key": key, "bias": bias, "signed_weight": (w if bias == "多" else -w if bias == "空" else 0)})

    light("OIL_STRONG_GREEN", oil20 < -20, "多", 3)
    light("OIL_WEAK_GREEN", -20 <= oil20 < -10, "多", 1)
    light("GSR_CHEAP_GREEN", gz > 1, "多", 2)
    # 地緣狀態機(零落後)
    if oil20 >= 10 and gsr20 < 0:
        geo = {"light": "🟠 警示", "up_rate": 44.6}
    elif oil20 >= 10 and gsr20 >= 0:
        geo = {"light": "🟢 偏多", "up_rate": 62.7}
    else:
        geo = {"light": "🟢 中性偏多", "up_rate": 55.5}
    vix_env = "有效環境(VIX>=15)" if vix >= 15 else "鈍化環境(VIX<15,均值回歸訊號打折)"

    # --- 綜合傾向 ---
    score = sum(f["signed_weight"] for f in fired) + sum(l["signed_weight"] for l in lights)
    th = rb["composite"]["tilt_thresholds"]
    if score >= 5:
        tilt = "偏多(高信心)"
    elif score >= 2:
        tilt = "偏多(低信心)"
    elif score >= -1:
        tilt = "觀望"
    else:
        tilt = "偏空"
    return {"fired": fired, "lights": lights, "geo": geo, "vix_env": vix_env,
            "score": score, "tilt": tilt}

# ---------- 輸出 ----------
def render(rb, m, ev):
    L = []
    L.append("=" * 64)
    L.append(f"  白銀每日傾向工具  |  銀 ${m['silver']}  ({m['silver_date']})")
    L.append("=" * 64)
    L.append(f"金 ${m['gold']} | 金銀比 {m['gsr']} (5日{m['gsr_5d_chg']:+}/z {m['gsr_z250']:+}) | VIX {m['vix']} | 油20日 {m['oil_20d_pct']:+}%")
    cot = m.get("cot", {})
    if "error" not in cot:
        L.append(f"COT淨多 {cot['net']} (52週pct {cot['pct52']}, 4週變動 {cot['net4']:+}) @{cot['date']}")
        # 空頭顯示層(查證數據,非進場訊號):雙尺度 + 絕對口數 + 全距,缺一會誤導
        if "short" in cot:
            L.append(f"COT投機空單 {cot['short']} 口 "
                     f"(26週pct {cot['short_pct26']}% / 52週pct {cot['short_pct52']}% / "
                     f"5年pct {cot['short_pct260']}%, 4週 {cot['short_net4']:+})")
            L.append(f"   ↳ 26週全距僅 {cot['short_range26']} 口、空單/OI {cot['short_oi_pct']}% "
                     f"→ 空頭在近半年區間相對高、放5年仍偏低,燃料池「有累積、尚不算大」")
            L.append(f"   ⚠ COT落後約10天(此為 {cot['date']} 持倉);原始口數跨5年受OI時代漂移影響不可比;"
                     f"此為週級結構查證數據,非進場/出場訊號")
    L.append(f"200日均 ${m['ma200']} | 20日低 ${m['low20']}")
    L.append("-" * 64)
    L.append(f"🧭 綜合傾向: 【{ev['tilt']}】  (分數 {ev['score']:+})")
    L.append(f"   VIX 環境: {ev['vix_env']}")
    L.append(f"   地緣狀態: {ev['geo']['light']} (歷史上漲率 {ev['geo']['up_rate']}%)")
    L.append("-" * 64)
    if ev["fired"]:
        L.append("✅ 觸發的進場訊號:")
        for f in ev["fired"]:
            L.append(f"   [{f['key']}] {f['rule']}")
            L.append(f"       方向:{f['dir']} | 判定:{f['verdict']} | US {f['US']} | 命中率{f['hit']}% (N={f['N']})")
            L.append(f"       賭錯中位 {f['when_wrong_med']}% / 最壞 {f['when_wrong_worst']}%")
            L.append(f"       ⚠ {f['caveat']}")
    else:
        L.append("✅ 觸發的進場訊號: 無")
    if ev["lights"]:
        L.append("💡 觸發的背景燈: " + ", ".join(l["key"] for l in ev["lights"]))
    L.append("-" * 64)
    if ev["tilt"] == "觀望":
        L.append("📌 今日無可獨立進場訊號觸發 → 建議觀望,不硬找方向。")
    L.append("📎 提醒: 工具偏多側訊號較可靠,偏空側結構性失效(見 rulebook)。")
    L.append("        想做空時本工具能幫的有限,需靠籌碼/實體機制證據,不能靠回測。")
    L.append("=" * 64)
    return "\n".join(L)

def main():
    rb = json.load(open(RULEBOOK, encoding="utf-8"))
    m = compute(rb)
    ev = evaluate(rb, m)
    out = render(rb, m, ev)
    print(out)
    # 存一份 json 供程式化使用
    snap = {"asof": str(dt.date.today()), "metrics": m, "eval": {
        "tilt": ev["tilt"], "score": ev["score"], "vix_env": ev["vix_env"],
        "geo": ev["geo"], "fired": [f["key"] for f in ev["fired"]],
        "lights": [l["key"] for l in ev["lights"]]}}
    json.dump(snap, open(os.path.join(HERE, "last_run.json"), "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
