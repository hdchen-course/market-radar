#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
開盤前戰略定調儀表板 v3 (Strategic Pre-Market Dashboard)
========================================================
一行指令抓資料 → 寫固定 HTML → 美股開盤(台北 22:30 冬令)前 10 秒看一眼，
對「當週風險取向(Risk-on/off)」「今日日內形態(大單邊 vs 震盪)」「槓桿 ETF 燈號」有非黑即白藍圖。

目標槓桿 ETF(5 組多空成對)：
  QQQ   TQQQ(3x多)/SQQQ(3x空)   半導體 SOXL(3x多)/SOXS(3x空)
  MSTR  MSTU(2x多)/MSTZ(2x空)    NVDA   NVDL(2x多)/NVD(2x空)   SK Hynix SKUU(2x多)/SKDD(2x空)

設計：純標準庫·無 LLM·抓不到顯示 N/A 絕不編。門檻權重集中於 CONFIG。
  三主題可切換(--theme)：midnight(深色交易台) / cream(暖白雜誌) / nordic(霧藍柔和)。
  所有數值列 = 三欄對齊表格(標籤｜數值｜漲跌，等寬數字右對齊)。
  風控/量化/資料源三 lens 已落地：資料覆蓋閘、US10Y 雙 regime、VXN band 對齊 VIX×1.2、
  高波動禁網格、死貓彈防呆、紅燈不暗示反手、ETF 申贖以 RVOL 代理、盤前量用 NQ=F。

用法：
  signals/.venv/bin/python strategic_dashboard.py                 # 預設主題 nordic
  signals/.venv/bin/python strategic_dashboard.py --theme midnight --open
  signals/.venv/bin/python strategic_dashboard.py --catalyst "CPI"   # 當日有重大事件
  signals/.venv/bin/python strategic_dashboard.py --all              # 一次產 3 主題(挑風格用)
"""
import sys, os, json, ssl, time, argparse, datetime, urllib.request, urllib.parse
import re
import concurrent.futures as _cf
from email.utils import parsedate_to_datetime
from collections import defaultdict

TPE = datetime.timezone(datetime.timedelta(hours=8))

# ============================== CONFIG ==============================
RISK_WEIGHTS = {"vxn": 26, "vix": 12, "dxy": 14, "us10y": 22, "dvol": 14, "fng": 12}
VXN_BANDS  = [(20, 10), (26, 35), (32, 60), (40, 85), (999, 100)]
VIX_BANDS  = [(15, 10), (20, 35), (25, 60), (32, 85), (999, 100)]
DVOL_BANDS = [(45, 20), (55, 45), (70, 70), (90, 90), (999, 100)]
FNG_BANDS  = [(20, 90), (35, 70), (55, 45), (75, 30), (100, 20)]
RISK_LABELS = [(35, "🟢 Risk-On（可進攻）", "ok"), (60, "🟡 中性偏謹慎", "warn"),
               (100, "🔴 Risk-Off（手收起來/偏防守）", "danger")]
COVERAGE_MIN = 0.80

TREND_WEIGHTS = {"gap": 35, "catalyst": 25, "premkt_rvol": 25, "dvol_chg": 15}
GAP_BANDS     = [(0.2, 15), (0.4, 35), (0.7, 60), (1.1, 82), (999, 95)]
PREMKT_BANDS  = [(0.8, 20), (1.2, 40), (1.8, 65), (2.5, 85), (999, 95)]
DVOLCHG_BANDS = [(2, 25), (6, 50), (12, 75), (999, 92)]
CATALYST_SCORE = 85
TREND_LABELS  = [(40, "💤 震盪/絞肉盤（槓桿 ETF 耗損地獄）", "mut"),
                 (60, "🌓 方向未定（偏震盪，留意變盤）", "warn"),
                 (100, "🚀 大單邊行情（順勢但必掛保本+開盤後確認）", "info")]

HARD_VOL_VXN = 28
HARD_VOL_DVOL = 70
RVOL_HOT = 1.5

ETF_PAIRS = [("QQQ", "TQQQ", "SQQQ", "3x"), ("半導體", "SOXL", "SOXS", "3x"),
             ("MSTR", "MSTU", "MSTZ", "2x"), ("NVDA", "NVDL", "NVD", "2x"),
             ("SK Hynix", "SKUU", "SKDD", "2x")]

# ── Fed 24h 放話掃描(資訊監控·非訊號;方向不可測、秒級被定價,勿因單則放話追單) ──
FED_PEOPLE = ["Powell", "Jefferson", "Bowman", "Waller", "Barr", "Cook", "Kugler", "Miran",
              "Barkin", "Bostic", "Daly", "Logan", "Goolsbee", "Musalem", "Schmid",
              "Hammack", "Collins", "Williams", "Harker", "Kashkari"]
FED_HAWK = ["hawkish", "higher for longer", "restrictive", "patient", "no rush", "inflation risk",
            "too soon", "caution", "premature", "rate hike", "hike"]
FED_DOVE = ["dovish", "rate cut", "cut rates", "easing", "soften", "weakening labor", "downside risk"]
FED_RSS = [("官方演講", "https://www.federalreserve.gov/feeds/speeches.xml", True),
           ("官方新聞稿", "https://www.federalreserve.gov/feeds/press_all.xml", False)]
FED_NEWS_Q = "(Fed OR Federal Reserve) (hawkish OR dovish OR rate cut OR rate hike OR inflation OR speech)"
FED_HOURS = 24

# ============================== 主題（美術設計 + 視覺醫生） ==============================
# 每個主題給一組 CSS 變數。color_for() 把語意 token(ok/warn/danger/info/mut) 對應到主題色。
THEMES = {
  "nordic": {   # 霧藍柔和 — 現代 SaaS、冷色淺底、柔和不刺眼
    "bg": "#eef2f7", "card": "#ffffff", "ink": "#263241", "mut": "#6b7684", "line": "#e3e8ef",
    "accent": "#4f7cb8", "ok": "#2e9e78", "dn": "#d2687a", "warn": "#c98a2e", "hot": "#bc6a1a",
    "warnbg": "#fff6ec", "warnbd": "#e3b877", "dangerbg": "#fdecef",
    "shadow": "0 1px 3px rgba(40,60,90,.07),0 8px 24px rgba(40,60,90,.05)", "font": '-apple-system,"Noto Sans TC",sans-serif',
  },
  "cream": {    # 暖白雜誌 FT — 米色紙感、沉穩墨色、磚紅不刺眼
    "bg": "#f4efe6", "card": "#fffdf8", "ink": "#2b2620", "mut": "#8a7f6d", "line": "#e9e1d2",
    "accent": "#3f5e8c", "ok": "#2f8f5b", "dn": "#bb4b38", "warn": "#b07d1f", "hot": "#a85d12",
    "warnbg": "#fbf3df", "warnbd": "#d8be7e", "dangerbg": "#f8e8e2",
    "shadow": "0 1px 2px rgba(80,60,30,.06),0 10px 26px rgba(80,60,30,.05)", "font": '"Noto Sans TC",-apple-system,sans-serif',
  },
  "midnight": { # 深色交易台 — 深藍炭底、金色重點、柔綠粉紅(非刺眼紅綠)
    "bg": "#0f131a", "card": "#171d27", "ink": "#e6edf3", "mut": "#8b97a7", "line": "#242c38",
    "accent": "#e3b341", "ok": "#3fb9a0", "dn": "#ff6b81", "warn": "#e3b341", "hot": "#f0a73a",
    "warnbg": "#241f12", "warnbd": "#6b5a2a", "dangerbg": "#2a1820",
    "shadow": "0 1px 3px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35)", "font": '-apple-system,"Noto Sans TC",sans-serif',
  },
}
DEFAULT_THEME = "cream"

def color_for(token, th):
    return th.get({"ok": "ok", "danger": "dn", "warn": "warn", "info": "accent", "mut": "mut"}.get(token, "mut"), th["mut"])

# ============================== 抓取 ==============================
_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
def _get(url, timeout=12):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout, context=_CTX) as r:
        return r.read().decode("utf-8", "replace")

def yahoo_chart(sym, rng="5d", interval="1d", prepost=False):
    q = urllib.parse.quote(sym, safe="=")
    pp = "&includePrePost=true" if prepost else ""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?interval={interval}&range={rng}{pp}"
    try:
        d = json.loads(_get(url))["chart"]["result"][0]; m = d["meta"]
        q0 = d.get("indicators", {}).get("quote", [{}])[0]
        closes = [c for c in q0.get("close", []) if c is not None]
        return {"price": m.get("regularMarketPrice"), "prev": m.get("chartPreviousClose"),
                "closes": closes, "vols": q0.get("volume", []), "ts": d.get("timestamp", []), "gmtoff": m.get("gmtoffset", 0)}
    except Exception as e:
        sys.stderr.write(f"[warn] yahoo {sym}: {e}\n")
        return {"price": None, "prev": None, "closes": [], "vols": [], "ts": [], "gmtoff": 0}

def binance(sym):
    try:
        d = json.loads(_get(f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={sym}"))
        return float(d["lastPrice"]), float(d["priceChangePercent"])
    except Exception as e:
        sys.stderr.write(f"[warn] binance {sym}: {e}\n"); return None, None

def deribit_dvol(cur="BTC"):
    now = int(time.time())
    url = ("https://www.deribit.com/api/v2/public/get_volatility_index_data?"
           f"currency={cur}&start_timestamp={(now-93600)*1000}&end_timestamp={now*1000}&resolution=3600")
    try:
        data = json.loads(_get(url))["result"]["data"]
        return (data[-1][4], data[0][4]) if data else (None, None)
    except Exception as e:
        sys.stderr.write(f"[warn] deribit: {e}\n"); return None, None

def fear_greed():
    try:
        d = json.loads(_get("https://api.alternative.me/fng/"))["data"][0]
        return int(d["value"]), d["value_classification"]
    except Exception as e:
        sys.stderr.write(f"[warn] fng: {e}\n"); return None, None

def premarket_rvol():
    r = yahoo_chart("NQ=F", rng="1mo", interval="5m", prepost=True)
    ts, vols, off = r["ts"], r["vols"], r["gmtoff"]
    if not ts or not vols: return None
    win = defaultdict(float)
    for t, v in zip(ts, vols):
        if not v: continue
        et = datetime.datetime.utcfromtimestamp(t + off); mins = et.hour*60 + et.minute
        if 8*60+30 <= mins < 9*60+30: win[et.date()] += v
    days = sorted(win)
    if len(days) < 6: return None
    base = [win[x] for x in days[-21:-1]]; avg = sum(base)/len(base) if base else 0
    return (win[days[-1]]/avg) if avg else None

def rvol_daily(sym):
    vols = [v for v in yahoo_chart(sym, rng="2mo")["vols"] if v]
    if len(vols) < 21: return None
    avg = sum(vols[-21:-1])/20
    return (vols[-1]/avg) if avg else None

def binance_equity_movers(n=10):
    """掃全部幣安美股永續(EQUITY/TradFi)，算 5 日%(最新vs5日前日線收)，回 (漲前n, 跌前n)。
       免維護清單——市場在炒哪個板塊一眼看出。失敗回 ([],[])。"""
    try:
        info = json.loads(_get("https://fapi.binance.com/fapi/v1/exchangeInfo"))
        syms = [s["symbol"] for s in info["symbols"]
                if s.get("underlyingType") == "EQUITY" and s.get("status") == "TRADING" and s["symbol"].endswith("USDT")]
    except Exception as e:
        sys.stderr.write(f"[warn] movers exchangeInfo: {e}\n"); return [], []
    def chg5(sym):
        try:
            k = json.loads(_get(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1d&limit=6"))
            if len(k) < 6: return None
            c0, c1 = float(k[0][4]), float(k[-1][4])
            return (sym[:-4], (c1/c0 - 1)*100, c1) if c0 else None
        except Exception:
            return None
    res = []
    try:
        with _cf.ThreadPoolExecutor(max_workers=16) as ex:
            for r in ex.map(chg5, syms, timeout=45):
                if r: res.append(r)
    except Exception as e:
        sys.stderr.write(f"[warn] movers klines: {e}\n")
    res.sort(key=lambda x: x[1], reverse=True)
    return res[:n], res[-n:][::-1]

def binance_equity_movers_24h(n=10):
    """掃全部幣安美股永續(EQUITY)，取 24h priceChangePercent，回 (漲前n, 跌前n)。
       用單一 /ticker/24hr 批次呼叫(一次回全部標的)省時——非逐檔打 klines。失敗回 ([],[])。
       註:EQUITY 永續 24h% 為滾動窗(含前一盤別),非當日 session;盤別敏感時以 Yahoo 當盤為準。"""
    try:
        info = json.loads(_get("https://fapi.binance.com/fapi/v1/exchangeInfo"))
        eq = {s["symbol"] for s in info["symbols"]
              if s.get("underlyingType") == "EQUITY" and s.get("status") == "TRADING" and s["symbol"].endswith("USDT")}
    except Exception as e:
        sys.stderr.write(f"[warn] movers24 exchangeInfo: {e}\n"); return [], []
    try:
        allt = json.loads(_get("https://fapi.binance.com/fapi/v1/ticker/24hr"))
    except Exception as e:
        sys.stderr.write(f"[warn] movers24 ticker: {e}\n"); return [], []
    res = []
    for t in (allt if isinstance(allt, list) else []):
        if t.get("symbol") in eq:
            try:
                res.append((t["symbol"][:-4], float(t["priceChangePercent"]), float(t["lastPrice"])))
            except (KeyError, ValueError, TypeError):
                continue
    res.sort(key=lambda x: x[1], reverse=True)
    return res[:n], res[-n:][::-1]

_FED_CACHE = {}
def _fed_items(xml):
    blocks = re.findall(r"<item>(.*?)</item>", xml, re.S) or re.findall(r"<entry>(.*?)</entry>", xml, re.S)
    out = []
    for it in blocks:
        tm = re.search(r"<title>(.*?)</title>", it, re.S)
        dm = re.search(r"<(?:pubDate|updated|published)>(.*?)</", it, re.S)
        title = re.sub(r"<!\[CDATA\[|\]\]>", "", tm.group(1)).strip() if tm else ""
        dt = None
        if dm:
            try:
                dt = parsedate_to_datetime(dm.group(1).strip())
                dt = dt.replace(tzinfo=datetime.timezone.utc) if dt.tzinfo is None else dt
            except Exception:
                dt = None
        out.append((dt, title))
    return out

def fed_scan(hours=FED_HOURS):
    """Fed 過去 N 小時放話掃描:官方演講/新聞稿 RSS + Google News RSS。純標準庫、抓不到回 ok=False 顯示 N/A 不編。
       回傳 {"ok":bool, "items":[{dt,time,who,tone,title,src}]}(最新在前)。鷹/鴿為關鍵字粗判,非語氣判讀。"""
    if hours in _FED_CACHE:
        return _FED_CACHE[hours]
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    tpe = datetime.timezone(datetime.timedelta(hours=8))
    srcs = list(FED_RSS) + [("新聞", f"https://news.google.com/rss/search?q={urllib.parse.quote(FED_NEWS_Q)}"
                             f"+when:{max(1, hours // 24)}d&hl=en-US&gl=US&ceid=US:en", True)]
    items, ok_any = [], False
    for label, url, show_tone in srcs:
        try:
            xml = _get(url, timeout=15)
            ok_any = True
        except Exception as e:
            sys.stderr.write(f"[warn] fed {label}: {e}\n")
            continue
        for dt, title in _fed_items(xml):
            if not dt or dt < cutoff or not title:
                continue
            tl = title.lower()
            h, dv = sum(k in tl for k in FED_HAWK), sum(k in tl for k in FED_DOVE)
            tone = "hawk" if h > dv else ("dove" if dv > h else "")
            who = "/".join(p for p in FED_PEOPLE if re.search(rf"\b{p}\b", title))
            items.append({"dt": dt, "time": dt.astimezone(tpe).strftime("%m/%d %H:%M"),
                          "who": who, "tone": (tone if show_tone else ""), "title": title, "src": label})
    items.sort(key=lambda x: x["dt"], reverse=True)
    for it in items:
        del it["dt"]
    res = {"ok": ok_any, "items": items}
    _FED_CACHE[hours] = res
    return res

# ── 信用面即時燈號(去槓桿賣壓是否止穩的風向鏢) ──
_CREDIT_CACHE = {}
def _fred_last(code, n=6):
    """FRED csv 取最後 n 筆 (date,float)。抓不到或無值回 []。純標準庫。"""
    try:
        txt = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}", timeout=12)
    except Exception as e:
        sys.stderr.write(f"[warn] fred {code}: {e}\n"); return []
    out = []
    for line in txt.splitlines():
        parts = line.split(",")
        if len(parts) != 2:
            continue
        dt, val = parts[0].strip(), parts[1].strip()
        if dt in ("observation_date", "DATE") or val in ("", ".", "value"):
            continue
        try:
            out.append((dt, float(val)))
        except ValueError:
            continue
    return out[-n:]

def credit_scan():
    """信用面即時燈號：FRED HY/IG OAS(日頻·T+1) + HYG/JNK(盤中即時代理)。
       抓不到該欄回 None、全失敗 ok=False 顯示 N/A 不編。
       lamp: 綠=止穩 / 黃=觀察(壓力鎖在HY端) / 紅=擴散(HY+IG齊飆=系統性)。
       判定鐵則:HY 走闊+IG 不動=局部可控;HY+IG 同步大幅走闊才是系統性去槓桿(金/加密被拖下水的觸發線)。"""
    if "r" in _CREDIT_CACHE:
        return _CREDIT_CACHE["r"]
    def _etf(sym):
        r = yahoo_chart(sym)
        return {"price": r.get("price"), "chg": chg_vs_prev_close(r)}  # 昨收基準,非 meta.prev
    # 四個抓取平行跑：總延遲=最慢單一來源(FRED 可能慢)，不累加
    with _cf.ThreadPoolExecutor(max_workers=4) as ex:
        f_hy = ex.submit(_fred_last, "BAMLH0A0HYM2")
        f_ig = ex.submit(_fred_last, "BAMLC0A0CM")
        f_hyg = ex.submit(_etf, "HYG")
        f_jnk = ex.submit(_etf, "JNK")
        hy, ig, hyg, jnk = f_hy.result(), f_ig.result(), f_hyg.result(), f_jnk.result()
    ok = bool(hy or ig or hyg["price"] or jnk["price"])

    def _dir(series):
        if len(series) < 2:
            return None, None
        vals = [v for _, v in series]
        last, prev = vals[-1], vals[-2]
        d = "up" if last - prev > 0.005 else ("down" if prev - last > 0.005 else "flat")
        newhigh = last >= max(vals) - 1e-9
        return d, newhigh
    hy_dir, hy_nh = _dir(hy)
    ig_dir, ig_nh = _dir(ig)
    hv = [v for _, v in hy]; iv = [v for _, v in ig]
    hy_widen = (hv[-1] - hv[0]) if len(hv) >= 2 else None   # 視窗內(約近6筆)累計變動
    ig_widen = (iv[-1] - iv[0]) if len(iv) >= 2 else None
    # 系統性需「量級」門檻:HY 視窗內走闊≥50bp 且 IG≥15bp 且仍在走闊(IG微升5bp不算系統性)
    systemic = (hy_widen is not None and ig_widen is not None
                and hy_widen >= 0.5 and ig_widen >= 0.15 and ig_dir == "up")
    hyg_chg = hyg["chg"]

    if not ok or hy_dir is None:
        tok, label, why = "mut", "N/A", "FRED/Yahoo 來源本次抓取失敗或資料不足"
    elif systemic or (hy_nh and hy_dir == "up" and hyg_chg is not None and hyg_chg <= -1.0):
        tok, label = "danger", "🔴 擴散（信用壓力升）"
        why = ("HY+IG 同步大幅走闊＝系統性去槓桿升級，金/加密恐被一起拖下水"
               if systemic else "HY 利差續創高且 HYG 盤中重挫(≤-1%)＝信用壓力向外擴散")
    elif (hy_dir in ("down", "flat") and not hy_nh) and (hyg_chg is None or hyg_chg >= -0.3):
        tok, label = "ok", "🟢 止穩"
        why = "HY 利差不再創高、HYG 盤中未重挫＝信用面暫止穩(去槓桿賣壓近尾聲的必要條件之一)"
    else:
        tok, label = "warn", "🟡 觀察"
        why = "HY 利差仍走闊但 IG 大致穩＝壓力鎖在高收益/AI 端、尚未系統性；盯轉綠(止穩)或轉紅(HY+IG 齊飆)"

    res = {"ok": ok, "hy": hy, "ig": ig, "hyg": hyg, "jnk": jnk,
           "hy_dir": hy_dir, "hy_newhigh": hy_nh, "ig_dir": ig_dir, "ig_newhigh": ig_nh,
           "hy_widen": hy_widen, "ig_widen": ig_widen,
           "lamp": {"tok": tok, "label": label, "why": why}}
    _CREDIT_CACHE["r"] = res
    return res

def signal_strip(d, credit):
    """三訊號綜合狀態(一眼看齊:賣壓竭了沒)。①VIX 退潮? ②信用止穩? 自動亮燈;
       ③flush(賣壓竭)=intraday 深V+爆量,日線測不出→誠實標『人工確認』不假裝自動判定。
       門檻為啟發式(未回測),僅把使用者擋在『還在殺就別搶底』那側。"""
    vix = d.get("vix"); vchg = d.get("vix_chg")
    vtxt = f"{vchg:+.0f}%" if vchg is not None else "N/A"
    if vix is None:
        v = {"tok": "mut", "label": "VIX N/A", "detail": "資料不足"}
    elif vchg is not None and vchg <= -5 and vix < 28:
        v = {"tok": "ok", "label": "🟢 VIX 退潮中", "detail": f"VIX {vix:.1f}（{vtxt}）回落，vol-target/risk-parity 減壓趨緩"}
    elif vix >= 25 and (vchg is None or vchg >= 0):
        v = {"tok": "danger", "label": "🔴 VIX 高檔未退", "detail": f"VIX {vix:.1f}（{vtxt}），恐慌仍升/未收斂，波動型賣壓續燒"}
    elif vix < 18:
        v = {"tok": "ok", "label": "🟢 VIX 平靜", "detail": f"VIX {vix:.1f}，低波動"}
    else:
        v = {"tok": "warn", "label": "🟡 VIX 觀察", "detail": f"VIX {vix:.1f}（{vtxt}），未明確退潮"}
    lp = (credit or {}).get("lamp", {}) or {}
    c = {"tok": lp.get("tok", "mut"), "label": "信用 " + lp.get("label", "N/A"), "detail": lp.get("why", "")}
    fl = {"tok": "mut", "label": "⚪ 賣壓竭：需人工確認",
          "detail": "等開盤後『深 V 急拉收紅＋爆量』或『開盤砸不下去、尾盤收高』——intraday 反轉日線測不出，人工判讀"}
    toks = [v["tok"], c["tok"]]
    if "danger" in toks:
        overall = {"tok": "danger", "text": "賣方仍控場：VIX 未退潮或信用擴散，反彈先當逃命波、別搶底"}
    elif v["tok"] == "ok" and c["tok"] == "ok":
        overall = {"tok": "ok", "text": "初步轉穩：VIX 退潮＋信用止穩；惟 flush（賣壓竭）仍須人工確認才算見底"}
    else:
        overall = {"tok": "warn", "text": "分歧／觀察：尚未同時滿足 VIX 退潮與信用止穩，續盯"}
    return {"vix": v, "credit": c, "flush": fl, "overall": overall}

# ============================== 計分 ==============================
def band(v, bands):
    for hi, sc in bands:
        if v <= hi: return sc
    return bands[-1][1]
def pct(a, b): return (a/b - 1.0)*100.0 if (a is not None and b not in (None, 0)) else None
def _base_close(r):
    """前一交易日收盤基準。避開 Yahoo meta.chartPreviousClose 在多日 range 回傳
       『視窗起點前錨點』的灌水 bug（VIX 曾因此顯示 +56.7%，真實約 +26%）。
       規則:有≥2 根日線收盤時——若 closes[-1]≈現價(今日形成中/已收 K)→用 closes[-2](昨收)當基準;
       若 closes[-1] 與現價明顯不同(最後一根其實是昨日、今日尚無 K)→用 closes[-1](昨收)。
       closes 不足才 fallback meta.prev。"""
    c = r.get("closes") or []; price = r.get("price")
    if price is not None and len(c) >= 2:
        return c[-2] if abs(c[-1] - price) <= abs(price) * 1e-4 else c[-1]
    if len(c) >= 2:
        return c[-2]
    return r.get("prev")
def chg_vs_prev_close(r):
    """現價 vs 前一交易日收盤 %（取代 pct(price, meta.prev) 的基準 bug）。"""
    return pct(r.get("price"), _base_close(r))
def ma(xs, n): return sum(xs[-n:])/min(len(xs), n) if xs else None
def weighted(sub, w):
    num = den = 0.0
    for k, ww in w.items():
        if sub.get(k) is not None: num += sub[k]*ww; den += ww
    return (num/den if den else None), den
def pick(v, labels):
    for hi, txt, tok in labels:
        if v <= hi: return txt, tok
    return labels[-1][1], labels[-1][2]
def us10y_subscore(dbps, stress):
    if dbps is None: return None
    if dbps >= 8: return 85
    if dbps > 3: return 70
    if dbps >= -3: return 50
    if stress: return 95 if dbps < -8 else 75
    return 15 if dbps < -8 else 30

def collect(catalyst):
    d = {}
    vix = yahoo_chart("^VIX"); vxn = yahoo_chart("^VXN")
    d["vix"], d["vxn"] = vix["price"], vxn["price"]
    d["vix_chg"], d["vxn_chg"] = chg_vs_prev_close(vix), chg_vs_prev_close(vxn)
    dxy = yahoo_chart("DX-Y.NYB", rng="1mo"); d["dxy"] = dxy["price"]
    d["dxy_ma20"] = ma(dxy["closes"], 20); d["dxy_dev"] = pct(dxy["price"], d["dxy_ma20"])
    t10 = yahoo_chart("^TNX"); d["us10y"] = t10["price"]
    _t10b = _base_close(t10)
    d["us10y_bps"] = (t10["price"] - _t10b)*100 if (t10["price"] is not None and _t10b is not None) else None
    d["us30y"] = yahoo_chart("^TYX")["price"]; d["us2y"] = yahoo_chart("2YY=F")["price"]; d["us3m"] = yahoo_chart("^IRX")["price"]
    d["spread_2s10s"] = (d["us10y"] - d["us2y"]) if (d["us10y"] and d["us2y"]) else None
    es = yahoo_chart("ES=F", rng="5d"); nq = yahoo_chart("NQ=F", rng="5d")
    d["es_gap"], d["nq_gap"] = chg_vs_prev_close(es), chg_vs_prev_close(nq)
    nqc = nq["closes"]; d["nq_yday"] = pct(nqc[-1], nqc[-2]) if len(nqc) >= 2 else None
    dvol, dvp = deribit_dvol("BTC"); d["dvol"], d["dvol_chg"] = dvol, pct(dvol, dvp)
    d["fng"], d["fng_cls"] = fear_greed()
    d["wti"] = yahoo_chart("CL=F")["price"]; d["brent"] = yahoo_chart("BZ=F")["price"]
    for k, s in [("xau", "XAUUSDT"), ("xag", "XAGUSDT"), ("xpt", "XPTUSDT"), ("xpd", "XPDUSDT"),
                 ("tbt", "TBTUSDT"), ("gdx", "GDXUSDT"), ("bito", "BITOUSDT")]:
        d[k], d[k+"_chg"] = binance(s)
    d["binance"] = {}
    for name, s in [("BTC", "BTCUSDT"), ("ETH", "ETHUSDT"), ("MSTR", "MSTRUSDT"), ("NVDA", "NVDAUSDT")]:
        d["binance"][name] = binance(s)
    d["etf"] = {}
    for grp, lng, shrt, mult in ETF_PAIRS:
        rl = yahoo_chart(lng, rng="5d"); rs = yahoo_chart(shrt, rng="5d")
        d["etf"][grp] = {"long": lng, "short": shrt, "mult": mult,
                         "long_chg": chg_vs_prev_close(rl), "short_chg": chg_vs_prev_close(rs),
                         "rvol": rvol_daily(lng)}
    d["premkt_rvol"] = premarket_rvol(); d["catalyst"] = catalyst
    d["movers_up"], d["movers_dn"] = binance_equity_movers(10)
    d["movers24_up"], d["movers24_dn"] = binance_equity_movers_24h(10)
    return d

def score_riskoff(d):
    stress = ((d["vxn_chg"] or 0) > 5) or ((d["nq_gap"] or 0) <= -0.5) or ((d["vix"] or 0) >= 22)
    sub = {"vxn": band(d["vxn"], VXN_BANDS) if d["vxn"] is not None else None,
           "vix": band(d["vix"], VIX_BANDS) if d["vix"] is not None else None,
           "dvol": band(d["dvol"], DVOL_BANDS) if d["dvol"] is not None else None,
           "fng": band(d["fng"], FNG_BANDS) if d["fng"] is not None else None,
           "us10y": us10y_subscore(d["us10y_bps"], stress),
           "dxy": max(10, min(95, 50 + d["dxy_dev"]*15)) if d["dxy_dev"] is not None else None}
    total, den = weighted(sub, RISK_WEIGHTS)
    return total, sub, den/sum(RISK_WEIGHTS.values()), stress

def score_trend(d):
    gap = max(abs(d["es_gap"] or 0), abs(d["nq_gap"] or 0)) if (d["es_gap"] is not None or d["nq_gap"] is not None) else None
    sub = {"gap": band(gap, GAP_BANDS) if gap is not None else None,
           "catalyst": CATALYST_SCORE if d["catalyst"] else None,
           "premkt_rvol": band(d["premkt_rvol"], PREMKT_BANDS) if d["premkt_rvol"] is not None else None,
           "dvol_chg": band(abs(d["dvol_chg"]), DVOLCHG_BANDS) if d["dvol_chg"] is not None else None}
    total, _ = weighted(sub, TREND_WEIGHTS)
    return total, sub, gap

def breadth(d):
    chg = [d["etf"][g[0]]["long_chg"] for g in ETF_PAIRS if d["etf"][g[0]]["long_chg"] is not None]
    up = sum(1 for c in chg if c > 0); dn = sum(1 for c in chg if c < 0); n = len(chg)
    if n == 0: return "N/A", "mut", 0, 0, 0
    if up >= 4: return "📈 全面上漲（多頭 ETF 普漲）", "ok", up, dn, n
    if dn >= 4: return "📉 全面下殺（多頭 ETF 普跌）", "danger", up, dn, n
    return "🔀 板塊分化（有漲有跌）", "warn", up, dn, n

def lights(riskoff, trend, coverage, d):
    out = []
    data_bad = coverage < COVERAGE_MIN or d["vix"] is None or d["vxn"] is None
    vxn_hot = (d["vxn"] or 0) >= HARD_VOL_VXN
    deadcat = (d["nq_yday"] is not None and d["nq_yday"] <= -2 and (d["nq_gap"] or 0) > 0)
    def base(grp, hi_beta=False):
        if data_bad: return (grp, "🔴 資料不全＝不可交易", "danger", "VIX/VXN 缺或覆蓋<80%，視同高風險")
        if riskoff is not None and riskoff >= 70: return (grp, "🔴 空手不碰（別做多、也別抄底搶反彈）", "danger", f"Risk-Off {riskoff:.0f}≥70")
        if vxn_hot: return (grp, "🔴 空手不碰：高波動禁網格", "danger", f"VXN {d['vxn']:.0f}≥{HARD_VOL_VXN}，震盪對槓桿 ETF 最貴")
        if trend is not None and trend >= 60:
            if deadcat: return (grp, "🟡 跳空反抽≠趨勢：禁追，需開盤後確認", "warn", "昨大跌今跳空漲＝反轉風險(gap-and-fade)")
            return (grp, "🟢 單邊動能（順勢·必掛保本·開盤後確認才進）", "ok", f"大單邊 {trend:.0f}%" + ("＋半導體 beta 最大" if hi_beta else ""))
        if trend is not None and trend < 40: return (grp, "🟡 微幅網格（0.3~0.5% 立即保本，或不碰）", "warn", f"震盪 {100-trend:.0f}%")
        return (grp, "🌓 方向未定，等開盤確認", "warn", "形態中性")
    out.append(base("TQQQ / SQQQ")); out.append(base("SOXL / SOXS", True))
    out.append(base("NVDL / NVD")); out.append(base("SKUU / SKDD"))
    if data_bad:
        out.append(("MSTU / MSTZ", "🔴 資料不全＝不可交易", "danger", "覆蓋不足"))
    elif (d["dvol"] or 0) >= HARD_VOL_DVOL or (d["dvol_chg"] or 0) >= 6 or (riskoff or 0) >= 60:
        why = []
        if (d["dvol"] or 0) >= HARD_VOL_DVOL: why.append(f"BTC DVOL {d['dvol']:.0f} 高檔")
        if (d["dvol_chg"] or 0) >= 6: why.append(f"DVOL ~24h {d['dvol_chg']:+.0f}%")
        if (riskoff or 0) >= 60: why.append(f"Risk-Off {riskoff:.0f}")
        out.append(("MSTU / MSTZ", "🔴 風險極高，空手觀望", "danger", "、".join(why)))
    else:
        out.append(("MSTU / MSTZ", "🟡 中性：MSTR 另有 MSCI/mNAV 特異事件，需另查", "warn", f"BTC DVOL {d['dvol']:.0f}" if d["dvol"] else "DVOL N/A"))
    return out, data_bad, deadcat

# ============================== HTML ==============================
def f(v, suf="", dp=2, plus=False):
    if v is None: return '<span class="na">N/A</span>'
    return (f"{v:+.{dp}f}" if plus else f"{v:.{dp}f}") + suf
def chg_cell(c, dp=2):
    if c is None: return '<span class="na">N/A</span>'
    cls = "up" if c > 0 else "dn" if c < 0 else "fl"
    return f'<span class="{cls}">{c:+.{dp}f}%</span>'

STRUCT_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font);background:var(--bg);color:var(--ink);padding:18px;line-height:1.5;font-size:15px}
.wrap{max-width:1680px;margin:0 auto}
h1{font-size:1.3rem;text-align:center;letter-spacing:.5px}
.sub{text-align:center;color:var(--mut);font-size:.8rem;margin:4px 0 10px}
.topbar{background:var(--warnbg);border:1px solid var(--warnbd);border-radius:10px;padding:10px 15px;font-size:.82rem;color:var(--ink);margin-bottom:12px;text-align:center}
.covrow{text-align:center;margin-bottom:12px;font-size:.82rem;color:var(--mut)}
.cov-ok{color:var(--ok);font-weight:700} .cov-bad{color:var(--dn);font-weight:800;background:var(--dangerbg);padding:4px 12px;border-radius:20px}
.warnline{background:var(--dangerbg);border:1px solid var(--dn);color:var(--dn);border-radius:8px;padding:8px 13px;font-size:.8rem;margin-bottom:11px;font-weight:600;text-align:center}
.breadth{text-align:center;font-size:1.1rem;font-weight:800;padding:11px;border-radius:12px;margin-bottom:13px;background:var(--card);box-shadow:var(--shadow)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.card{background:var(--card);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow)}
.card h2{font-size:.92rem;margin-bottom:12px;color:var(--accent);font-weight:800;display:flex;align-items:center;gap:7px}
.card h2::before{content:"";width:4px;height:15px;background:var(--accent);border-radius:2px;display:inline-block}
.big{text-align:center;padding:4px 0 12px}
.gauge{font-size:2.7rem;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.glabel{font-size:1.05rem;font-weight:800;margin-top:7px}
.bar{height:10px;border-radius:6px;background:var(--line);overflow:hidden;margin:11px auto;max-width:92%}
.bar>i{display:block;height:100%;border-radius:6px}
.mini{font-size:.72rem;color:var(--mut)}
.split{display:flex;gap:12px}.split>div{flex:1;text-align:center}
/* 對齊表格列：標籤 | 數值 | 漲跌，數字等寬右對齊 */
.row{display:grid;grid-template-columns:1fr 92px 92px;gap:8px;align-items:baseline;padding:6px 0;border-bottom:1px solid var(--line);font-size:.85rem}
.row:last-child{border-bottom:none}
.row .lbl{color:var(--mut)} .row .lbl .mut{color:var(--mut)}
.row .val,.row .chg{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.tbl{width:100%;border-collapse:collapse;font-size:.84rem}
.tbl th,.tbl td{padding:8px 8px;border-bottom:1px solid var(--line)}
.tbl th{color:var(--mut);font-weight:600;font-size:.74rem;text-align:left}
.tbl td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.tbl td.g{font-weight:800}
.up{color:var(--ok)} .dn{color:var(--dn)} .fl{color:var(--mut)}
.na{color:var(--mut);opacity:.8} .mut{color:var(--mut);font-size:.76rem;font-weight:400} .hot{color:var(--hot);font-weight:700}
.sec{font-size:.95rem;color:var(--accent);font-weight:800;margin:16px 0 9px;display:flex;align-items:center;gap:7px}
.sec::before{content:"";width:4px;height:16px;background:var(--accent);border-radius:2px;display:inline-block}
.lights{display:flex;flex-direction:column;gap:9px}
.light{background:var(--card);border-left:6px solid var(--mut);border-radius:12px;padding:12px 15px;box-shadow:var(--shadow)}
.lname{font-size:.8rem;color:var(--mut);font-weight:600} .lsig{font-size:1.02rem;font-weight:800;margin:3px 0} .lwhy{font-size:.76rem;color:var(--mut)}
.foot{color:var(--mut);font-size:.72rem;margin-top:18px;border-top:1px solid var(--line);padding-top:11px;line-height:1.6}
.ratebox{margin-top:10px;padding:11px 13px;background:var(--warnbg);border:1px solid var(--line);border-radius:10px}
.rb-h{font-size:.8rem;font-weight:800;color:var(--accent);margin-bottom:6px}
.rb-i{font-size:.76rem;color:var(--ink);line-height:1.6;margin:3px 0}
"""

def build_style(th):
    rootvars = ";".join(f"--{k}:{v}" for k, v in th.items())
    return f"<style>:root{{{rootvars}}}\n{STRUCT_CSS}</style>"

def render(d, riskoff, rsub, coverage, trend, tsub, gap, lts, data_bad, deadcat, stress, theme):
    th = THEMES[theme]; now = datetime.datetime.now(TPE).strftime("%Y-%m-%d %H:%M:%S")
    def C(tok): return color_for(tok, th)
    r_txt, r_tok = (pick(riskoff, RISK_LABELS) if (riskoff is not None and not data_bad) else ("⚠ 資料不全＝視同不可交易", "danger"))
    r_col = C(r_tok)
    t_txt, t_tok = pick(trend, TREND_LABELS) if trend is not None else ("N/A", "mut")
    ro = f"{riskoff:.0f}" if riskoff is not None else "—"
    single = f"{trend:.0f}" if trend is not None else "—"; chop = f"{100-trend:.0f}" if trend is not None else "—"
    cov_n = sum(1 for k in RISK_WEIGHTS if rsub.get(k) is not None)
    br_txt, br_tok, up, dn, nn = breadth(d); br_col = C(br_tok)
    dxy_tr = ("📈 強勢" if (d["dxy_dev"] or 0) > 0.1 else "📉 弱勢" if (d["dxy_dev"] or 0) < -0.1 else "➖ 持平")
    prv = d["premkt_rvol"]
    prv_main = f"{prv:.1f}×" if prv else "N/A"
    prv_tag = ("📊 暴量" if (prv and prv >= RVOL_HOT) else "💤 量縮" if (prv and prv < 0.8) else "")

    def row(lbl, val, chg=""):
        return f'<div class="row"><div class="lbl">{lbl}</div><div class="val">{val}</div><div class="chg">{chg}</div></div>'

    # A 風險
    a_rows = (
        row(f'美元 DXY <span class="mut">{dxy_tr}</span>', f(d['dxy']), f(d['dxy_dev'], '%', plus=True)) +
        row('10Y 殖利率', f(d['us10y'], '%'), f(d['us10y_bps'], 'bp', dp=1, plus=True)) +
        row('2Y / 10Y 利差', f(d['us2y'], '%'), f(d['spread_2s10s'], '', plus=True)) +
        row('3M / 30Y', f(d['us3m'], '%'), f(d['us30y'], '%')) +
        row('納指恐慌 VXN', f(d['vxn'], dp=1), chg_cell(d['vxn_chg'], 1)) +
        row('標普恐慌 VIX', f(d['vix'], dp=1), chg_cell(d['vix_chg'], 1)) +
        row('BTC 隱波 DVOL', f(d['dvol'], dp=1), chg_cell(d['dvol_chg'], 1)) +
        row('加密 F&amp;G', (str(d['fng']) if d['fng'] is not None else 'N/A'), (d['fng_cls'] or '')))
    # B 形態
    b_rows = (
        row('ES 期貨 vs 昨收（盤前高/低開）', '', chg_cell(d['es_gap'])) +
        row('NQ 期貨 vs 昨收（盤前高/低開）', f'<span class="mut">昨日收盤 {f(d["nq_yday"],"%",dp=1,plus=True)}</span>', chg_cell(d['nq_gap'])) +
        row('盤前期貨量能 RVOL', f'<span class="mut">{prv_tag}</span>', f'<span class="{"hot" if prv_tag=="📊 暴量" else ""}">{prv_main}</span>') +
        row('DVOL ~24h 變動', '', chg_cell(d['dvol_chg'], 1)) +
        row('當日重大事件', (d['catalyst'] or '<span class="na">無/未設</span>'), '') +
        row('原油 WTI / Brent', f(d['wti'], dp=1), f(d['brent'], dp=1)))
    # C ETF 表
    etf_rows = ""
    for grp, lng, shrt, mult in ETF_PAIRS:
        e = d["etf"][grp]; rv = e["rvol"]
        rvtxt = (f'<span class="{"hot" if rv>=RVOL_HOT else "mut"}">{rv:.1f}×</span>' if rv else '<span class="na">N/A</span>')
        etf_rows += (f'<tr><td class="g">{grp}</td><td>{lng} <span class="mut">{mult}多</span></td>'
                     f'<td class="num">{chg_cell(e["long_chg"])}</td><td>{shrt} <span class="mut">空</span></td>'
                     f'<td class="num">{chg_cell(e["short_chg"])}</td><td class="num">{rvtxt}</td></tr>')
    # E 幣安（對齊：名稱 | 價格 | 漲跌）
    e_rows = ""
    for name, (p, c) in d["binance"].items():
        e_rows += f'<tr><td class="g">{name}</td><td class="num">{f(p,dp=2) if p else "N/A"}</td><td class="num">{chg_cell(c)}</td></tr>'
    for name, key in [("黃金 XAU", "xau"), ("白銀 XAG", "xag"), ("鉑 XPT", "xpt"), ("鈀 XPD", "xpd"),
                      ('TBT <span class="mut">2x空長債=多長端利率</span>', "tbt"),
                      ('GDX <span class="mut">金礦股·~2x金beta·含股市腿</span>', "gdx"),
                      ('BITO <span class="mut">1x BTC期貨ETF·有轉倉損耗</span>', "bito")]:
        e_rows += f'<tr><td class="g">{name}</td><td class="num">{f(d[key],dp=2) if d[key] else "N/A"}</td><td class="num">{chg_cell(d.get(key+"_chg"))}</td></tr>'

    def mv_rows(lst, pos):
        if not lst: return '<tr><td class="na" colspan="3">N/A（掃描失敗或無資料）</td></tr>'
        cls = "up" if pos else "dn"
        return "".join(f'<tr><td class="g">{s}</td><td class="num {cls}">{p:+.1f}%</td>'
                       f'<td class="num">{px:g}</td></tr>' for s, p, px in lst)
    movers_up = mv_rows(d.get("movers_up"), True)
    movers_dn = mv_rows(d.get("movers_dn"), False)
    movers24_up = mv_rows(d.get("movers24_up"), True)
    movers24_dn = mv_rows(d.get("movers24_dn"), False)

    light_rows = "".join(
        f'<div class="light" style="border-left-color:{C(tok)}"><div class="lname">👉 {n}</div>'
        f'<div class="lsig" style="color:{C(tok)}">{t}</div><div class="lwhy">{w}</div></div>'
        for n, t, tok, w in lts)
    cov_badge = (f'<span class="cov-bad">⚠ 資料覆蓋 {cov_n}/6（VIX/VXN 任一缺或<80% 即不可交易）</span>'
                 if data_bad else f'<span class="cov-ok">✅ 資料覆蓋 {cov_n}/6</span>')
    deadcat_note = '<div class="warnline">⚠ 偵測到「昨日大跌＋今日跳空上漲」＝反轉風險(gap-and-fade)，綠燈禁用、需開盤後確認</div>' if deadcat else ''
    stress_tag = "　｜股市壓力旗標 ON(避險共振)" if stress else ""

    # G. Fed 24h 放話掃描(資訊監控·非訊號)
    fed = fed_scan(FED_HOURS)
    if not fed["ok"]:
        fed_body = '<tr><td class="na" colspan="4">N/A（RSS 來源本次抓取失敗）</td></tr>'
    elif not fed["items"]:
        fed_body = f'<tr><td class="na" colspan="4">過去 {FED_HOURS} 小時無相符條目</td></tr>'
    else:
        _tone_tag = {"hawk": '<span class="dn">🦅鷹</span>', "dove": '<span class="up">🕊鴿</span>', "": ""}
        fed_body = "".join(
            f'<tr><td class="mut">{it["time"]}</td>'
            f'<td class="g">{it["who"] or ""}</td>'
            f'<td>{it["title"][:90]}</td>'
            f'<td class="num">{_tone_tag[it["tone"]]}</td></tr>'
            for it in fed["items"][:14])
    fed_section = (f'<div class="sec">G. Fed 過去 {FED_HOURS} 小時放話掃描'
                   f'<span class="mut" style="margin-left:8px">資訊監控·非訊號·鷹/鴿為關鍵字粗判</span></div>'
                   f'<div class="card" style="padding:6px 18px">'
                   f'<table class="tbl"><tr><th>時間(台北)</th><th>講者</th><th>標題</th>'
                   f'<th style="text-align:right">傾向</th></tr>{fed_body}</table>'
                   f'<div class="mini" style="padding:8px 0">💡 Fed 官員放話會動盤但方向不可測、秒級被定價；'
                   f'當盤前背景資訊,勿因單則放話追單。來源:聯準會官方 RSS + Google News RSS(免費)。</div></div>')

    # H. 信用面即時燈號(HY/IG OAS + HYG/JNK)
    cr = credit_scan()
    _dirtag = lambda dr: {"up": '<span class="dn">↑走闊</span>', "down": '<span class="up">↓收斂</span>',
                          "flat": '<span class="mut">→持平</span>'}.get(dr, "—")
    _series = lambda s: (" → ".join(f"{v:.2f}" for _, v in s) if s else "N/A")
    def _etf_cell(e):
        return (f'{e["price"]:.2f}（{chg_cell(e["chg"])}）' if e["price"] else '<span class="na">N/A</span>')
    if not cr["ok"]:
        credit_body = '<tr><td class="na" colspan="3">N/A（FRED/Yahoo 來源本次抓取失敗）</td></tr>'
    else:
        hy_last = f'{cr["hy"][-1][1]:.2f}%' if cr["hy"] else '<span class="na">N/A</span>'
        ig_last = f'{cr["ig"][-1][1]:.2f}%' if cr["ig"] else '<span class="na">N/A</span>'
        credit_body = (
            f'<tr><td class="g">HY OAS <span class="mut">高收益利差·T+1</span></td>'
            f'<td class="num">{hy_last} {_dirtag(cr["hy_dir"])}</td>'
            f'<td class="mut">近{len(cr["hy"])}筆 {_series(cr["hy"])}</td></tr>'
            f'<tr><td class="g">IG OAS <span class="mut">投資級利差·T+1</span></td>'
            f'<td class="num">{ig_last} {_dirtag(cr["ig_dir"])}</td>'
            f'<td class="mut">近{len(cr["ig"])}筆 {_series(cr["ig"])}</td></tr>'
            f'<tr><td class="g">HYG <span class="mut">高收益債ETF·盤中即時/領先</span></td>'
            f'<td class="num">{_etf_cell(cr["hyg"])}</td><td class="mut">盤中止跌回升=信用先穩(領先 FRED 一天)</td></tr>'
            f'<tr><td class="g">JNK <span class="mut">高收益債ETF·盤中即時</span></td>'
            f'<td class="num">{_etf_cell(cr["jnk"])}</td><td class="mut">與 HYG 互相印證</td></tr>')
    _lamp = cr["lamp"]
    credit_section = (
        f'<div class="sec">H. 信用面即時燈號（HY/IG 利差 + HYG/JNK）'
        f'<span class="mut" style="margin-left:8px">去槓桿賣壓是否止穩的風向鏢</span></div>'
        f'<div class="card" style="padding:10px 18px">'
        f'<div class="glabel" style="color:{C(_lamp["tok"])};font-size:1.1rem;font-weight:800">{_lamp["label"]}</div>'
        f'<div class="mini" style="margin:2px 0 8px">{_lamp["why"]}</div>'
        f'<table class="tbl"><tr><th>指標</th><th style="text-align:right">最新</th><th>近況 / 讀法</th></tr>{credit_body}</table>'
        f'<div class="mini" style="padding:8px 0">💡 🟢止穩 / 🟡觀察 / 🔴擴散。HY 走闊+IG 不動=壓力鎖在高收益/AI 端(可控)；'
        f'HY+IG 齊飆=系統性去槓桿(金/加密恐被拖下水)。FRED OAS 日頻 T+1(慢一天)，盤中以 HYG/JNK 領先判讀。'
        f'來源:FRED(BAMLH0A0HYM2 / BAMLC0A0CM)+Yahoo(HYG/JNK)。</div></div>')

    # 🚦 三訊號綜合狀態(一眼看齊) — 置頂
    strip = signal_strip(d, cr)
    def _schip(x):
        return (f'<div style="flex:1;min-width:210px;background:var(--card);border-left:6px solid {C(x["tok"])};'
                f'border-radius:12px;padding:10px 13px;box-shadow:var(--shadow)">'
                f'<div style="font-weight:800;color:{C(x["tok"])}">{x["label"]}</div>'
                f'<div class="mini">{x.get("detail","")}</div></div>')
    strip_html = (f'<div class="sec" style="margin-top:4px">🚦 三訊號綜合狀態（一眼看齊：賣壓竭了沒）</div>'
                  f'<div style="background:var(--card);border:1px solid var(--line);border-left:6px solid {C(strip["overall"]["tok"])};'
                  f'border-radius:12px;padding:10px 14px;margin-bottom:9px;font-weight:700;color:{C(strip["overall"]["tok"])}">'
                  f'{strip["overall"]["text"]}</div>'
                  f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:4px">'
                  f'{_schip(strip["vix"])}{_schip(strip["credit"])}{_schip(strip["flush"])}</div>'
                  f'<div class="mini" style="margin-bottom:10px">💡 ①VIX 退潮、②信用止穩自動亮燈；③賣壓竭(flush)是 intraday 深V+爆量，日線測不出＝人工確認。三個同時轉綠(flush 需人工)才算見底訊號，否則反彈先當逃命波。</div>')

    return f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>開盤前戰略定調儀表板</title>
{build_style(th)}</head><body><div class="wrap">
<h1>🧭 開盤前戰略定調儀表板</h1>
<div class="sub">台北 {now}｜槓桿 ETF(TQQQ/SOXL/MSTU/NVDL/SKUU…) 作戰藍圖｜啟發式規則層·非買賣建議·未回測·不臆測持倉</div>
<div class="topbar"><b>紀律鐵則：</b>資料不全(任一波動度 N/A)或開盤後 30 分未複查前，今日一律視為不可交易。本表只負責把你擋在爛盤外，<b>永遠不會叫你進場</b>——🟢綠燈不是進場令、🔴紅燈不是抄底/反手令；高波動的震盪盤對槓桿 ETF 是最貴的盤，寧可空手。</div>
<div class="covrow">{cov_badge}　｜　盤前快照，gap% 與盤前量在開盤那刻才定稿</div>
{deadcat_note}
<div class="breadth" style="color:{br_col}">{br_txt}　<span class="mini">(多頭 ETF {up}漲 / {dn}跌 / 共{nn})</span></div>

{strip_html}
<div class="grid">
  <div class="card">
    <h2>A. 當週風險取向風向球（看趨勢）</h2>
    <div class="big">
      <div class="gauge" style="color:{r_col}">{ro}<span style="font-size:1rem;color:var(--mut)">/100</span></div>
      <div class="glabel" style="color:{r_col}">{r_txt}</div>
      <div class="bar"><i style="width:{ro if ro!='—' else 0}%;background:{r_col}"></i></div>
      <div class="mini">0=極度 Risk-On　100=極度 Risk-Off{stress_tag}</div>
    </div>
    {a_rows}
    <div class="mini" style="margin-top:8px">💡 DXY 強+殖利率飆=全球抽資金(Risk-Off)；殖利率「崩跌且股市有壓」=避險共振(仍 Risk-Off)；VXN 骨架決定 TQQQ/SOXL 會不會暴走。</div>
    <div class="ratebox">
      <div class="rb-h">📐 利率怎麼看、怎麼用（對槓桿 ETF）</div>
      <div class="rb-i"><b>誰在動：</b>短端 <b>3M/2Y</b>＝Fed 政策利率（升降息）；長端 <b>10Y/30Y</b>＝市場對通膨+財政赤字+發債供給的定價（Fed 管不太到）。</div>
      <div class="rb-i"><b>殖利率「升」</b>＝壓高估值科技 → <b>TQQQ/SOXL/NVDL 偏空、TBT 偏多</b>；長端飆(30Y)更兇＝財政/供給警訊，股債雙殺。</div>
      <div class="rb-i"><b>殖利率「降」要分兩種</b>：① 鴿派預期(股市平靜)＝真 risk-on，科技偏多；② <b>避險崩跌(股市同時殺)＝risk-off，科技照跌、別搶反彈</b>（本表 US10Y 已用「股市壓力旗標」自動區分）。</div>
      <div class="rb-i"><b>2s10s 曲線：</b>負=<b>倒掛</b>(衰退前兆)；由負轉正(解除倒掛)常是衰退「正要開始」；熊陡(長端升)最傷科技、牛陡(短端降)偏利多。</div>
      <div class="rb-i"><b>一句話：</b>開盤前先看「殖利率往哪走＋股市有沒有同步壓力」→ 決定今天科技槓桿 ETF 是順勢偏空、還是鴿派可偏多；TBT 是長端利率的直接槓桿代理。</div>
    </div>
  </div>
  <div class="card">
    <h2>B. 今日日內形態預測（看形態）</h2>
    <div class="big">
      <div class="split">
        <div><div class="gauge" style="color:{C('info')};font-size:2rem">{single}%</div><div class="mini">大單邊機率</div></div>
        <div><div class="gauge" style="color:var(--mut);font-size:2rem">{chop}%</div><div class="mini">震盪機率</div></div>
      </div>
      <div class="glabel" style="color:{C(t_tok)};margin-top:9px">{t_txt}</div>
    </div>
    {b_rows}
    <div class="mini" style="margin-top:8px">💡「期貨 vs 昨收」＝盤前期貨相對昨日收盤偏離%(正=偏高開/risk-on、負=偏低開)，近似今日高/低開風向(非真正開盤跳空缺口)。偏離大+盤前暴量+重大事件=大單邊(順勢但掛保本)；偏離小+量縮=絞肉震盪(槓桿 ETF 耗損最兇，少碰)。盤前 VXN 變動是死值，已改用期貨 RVOL。</div>
  </div>
</div>

<div class="sec">C. 目標槓桿 ETF 漲跌 + 量能（RVOL=當日量/20日均，申贖無免費源之代理）</div>
<div class="card" style="padding:6px 18px">
<table class="tbl"><tr><th>組別</th><th>多頭 ETF</th><th style="text-align:right">昨漲跌</th><th>反向 ETF</th><th style="text-align:right">昨漲跌</th><th style="text-align:right">RVOL</th></tr>{etf_rows}</table>
</div>

<div class="grid" style="margin-top:15px">
  <div>
    <div class="sec">D. 各商品操作燈號（純數學 IF/THEN + 四道硬煞車）</div>
    <div class="lights">{light_rows}</div>
  </div>
  <div>
    <div class="sec">E. 幣安即時報價（標的 underlying + 貴金屬）</div>
    <div class="card" style="padding:6px 18px">
    <table class="tbl"><tr><th>標的</th><th style="text-align:right">價格</th><th style="text-align:right">24h 漲跌</th></tr>{e_rows}</table>
    <div class="mini" style="padding:8px 0">💡 槓桿 ETF 的「標的本體」即時價(24/7)，比延遲的 ETF 報價更快反映方向；貴金屬看避險腿是否也被拖(sell everything)。</div>
    </div>
  </div>
</div>

<div class="sec">F. 幣安美股永續 5 日漲跌榜（全 196 檔 EQUITY 自動掃描 → 市場在炒哪個板塊）</div>
<div class="grid">
  <div class="card" style="padding:6px 18px">
    <table class="tbl"><tr><th>📈 5 日漲幅前 10</th><th style="text-align:right">5日%</th><th style="text-align:right">現價</th></tr>{movers_up}</table>
  </div>
  <div class="card" style="padding:6px 18px">
    <table class="tbl"><tr><th>📉 5 日跌幅前 10</th><th style="text-align:right">5日%</th><th style="text-align:right">現價</th></tr>{movers_dn}</table>
  </div>
</div>
<div class="mini" style="margin:6px 2px 0">💡 全幣安美股永續(underlyingType=EQUITY)自動掃描、免維護清單；反向/做空VIX類ETF(SOXS/SQQQ/UVXY)衝上漲榜＝市場在避險/做空該板塊，做多槓桿ETF(SOXL/MUU/KORU)墊底＝該板塊被殺。5日%=最新vs5日前日線收。</div>

<div class="sec" style="margin-top:14px">F2. 幣安美股永續 24 小時漲跌榜（同一批 EQUITY → 最近一天在炒/在殺哪個）</div>
<div class="grid">
  <div class="card" style="padding:6px 18px">
    <table class="tbl"><tr><th>📈 24h 漲幅前 10</th><th style="text-align:right">24h%</th><th style="text-align:right">現價</th></tr>{movers24_up}</table>
  </div>
  <div class="card" style="padding:6px 18px">
    <table class="tbl"><tr><th>📉 24h 跌幅前 10</th><th style="text-align:right">24h%</th><th style="text-align:right">現價</th></tr>{movers24_dn}</table>
  </div>
</div>
<div class="mini" style="margin:6px 2px 0">💡 24h% 取自 /ticker/24hr 滾動窗(含前一盤別、非當日 session)；看「最近一天」板塊輪動與 5 日榜對照——24h 翻紅但 5 日仍墊底＝短線反彈 vs 24h 續殺＝趨勢未止。盤別敏感時當盤漲跌以 Yahoo 為準。</div>

{credit_section}

{fed_section}

<div class="foot">
  ⚠ 啟發式規則層(IF/THEN 門檻集中於程式 CONFIG、經驗權重未回測)，<b>非投資建議、不臆測你的持倉</b>。
  資料源：Yahoo chart(VIX/VXN/DXY/US2Y/10Y/30Y/3M/ES/NQ/ETF 日線)、Deribit(BTC DVOL)、Alternative.me(加密 F&amp;G)、Binance 永續(標的+貴金屬)。
  ETF 每日申贖無免費 API → 以 RVOL(當日量/20日均量，已與 Nasdaq API 交叉驗證)代理；盤前量用 NQ=F 5m includePrePost。
  三道專家 lens 已落地：資料覆蓋閘、US10Y 雙 regime、VXN band 對齊 VIX×1.2、高波動禁網格、死貓彈防呆、紅燈不暗示反手。主題：{theme}。台北 {now} 生成。
</div>
</div></body></html>"""

def dashboard_payload(catalyst=""):
    """抓資料＋計分＋結構化＝可共用的「儀表板資料單元」。
    /dailyecreport 報告流程直接 import 本函式取得 dashboard 區塊資料（同一份抓資料程式碼，不重複）；
    本檔 --embed-json 與（未來）JSON 版 viewer 也都用它。回傳純 dict（值皆為顯示字串，供前端暗色 render）。"""
    d = collect((catalyst or "").strip())
    riskoff, rsub, coverage, stress = score_riskoff(d)
    trend, tsub, gap = score_trend(d)
    lts, data_bad, deadcat = lights(riskoff, trend, coverage, d)
    fmtc = lambda v, suf="%", dp=2: f(v, suf, dp, plus=True)
    r_txt = (pick(riskoff, RISK_LABELS)[0] if (riskoff is not None and not data_bad) else "資料不全＝視同不可交易")
    t_txt = pick(trend, TREND_LABELS)[0] if trend is not None else "N/A"
    br_txt, br_tok, up, dn, nn = breadth(d)
    ro = f"{riskoff:.0f}" if riskoff is not None else "—"
    single = f"{trend:.0f}" if trend is not None else "—"
    chop = f"{100 - trend:.0f}" if trend is not None else "—"
    risk_rows = [
        {"lbl": "美元 DXY", "val": f(d['dxy']), "chg": fmtc(d['dxy_dev'])},
        {"lbl": "10Y 殖利率", "val": f(d['us10y'], '%'), "chg": fmtc(d['us10y_bps'], 'bp', 1)},
        {"lbl": "2Y / 10Y 利差", "val": f(d['us2y'], '%'), "chg": fmtc(d['spread_2s10s'], '', 2)},
        {"lbl": "3M / 30Y", "val": f(d['us3m'], '%'), "chg": f(d['us30y'], '%')},
        {"lbl": "納指恐慌 VXN", "val": f(d['vxn'], '', 1), "chg": fmtc(d['vxn_chg'], '%', 1)},
        {"lbl": "標普恐慌 VIX", "val": f(d['vix'], '', 1), "chg": fmtc(d['vix_chg'], '%', 1)},
        {"lbl": "BTC 隱波 DVOL", "val": f(d['dvol'], '', 1), "chg": fmtc(d['dvol_chg'], '%', 1)},
        {"lbl": "加密 F&G", "val": (str(d['fng']) if d['fng'] is not None else 'N/A'), "chg": (d['fng_cls'] or '')},
    ]
    trend_rows = [
        {"lbl": "ES 期貨 vs 昨收（盤前高/低開）", "val": "", "chg": fmtc(d['es_gap'])},
        {"lbl": "NQ 期貨 vs 昨收（盤前高/低開）", "val": f"昨日收盤 {fmtc(d['nq_yday'], '%', 1)}", "chg": fmtc(d['nq_gap'])},
        {"lbl": "盤前期貨量能 RVOL", "val": "", "chg": (f"{d['premkt_rvol']:.1f}×" if d['premkt_rvol'] else "N/A")},
        {"lbl": "DVOL ~24h 變動", "val": "", "chg": fmtc(d['dvol_chg'], '%', 1)},
        {"lbl": "當日重大事件", "val": (d['catalyst'] or "無/未設"), "chg": ""},
        {"lbl": "原油 WTI / Brent", "val": f(d['wti'], '', 1), "chg": f(d['brent'], '', 1)},
    ]
    etf = [{"grp": g[0], "long": d['etf'][g[0]]['long'], "mult": d['etf'][g[0]]['mult'],
            "long_chg": fmtc(d['etf'][g[0]]['long_chg']), "short": d['etf'][g[0]]['short'],
            "short_chg": fmtc(d['etf'][g[0]]['short_chg']),
            "rvol": (f"{d['etf'][g[0]]['rvol']:.1f}×" if d['etf'][g[0]]['rvol'] else "N/A")} for g in ETF_PAIRS]
    binance = [{"name": n, "price": (f(p, '', 2) if p else "N/A"), "chg": fmtc(c)} for n, (p, c) in d['binance'].items()]
    for nm, key in [("黃金 XAU", "xau"), ("白銀 XAG", "xag"), ("鉑 XPT", "xpt"), ("鈀 XPD", "xpd"),
                    ("TBT 2x空長債", "tbt"), ("GDX 金礦股", "gdx"), ("BITO 1xBTC期貨", "bito")]:
        binance.append({"name": nm, "price": (f(d[key], '', 2) if d[key] else "N/A"), "chg": fmtc(d.get(key + "_chg"))})
    lights_out = [{"name": n, "signal": t, "tok": tok, "why": w} for n, t, tok, w in lts]
    mv = lambda lst: [{"sym": s, "pct": f"{p:+.1f}%", "px": f"{px:g}"} for s, p, px in (lst or [])]
    summary = (f"Risk-Off {ro}/100（{r_txt}）｜日內大單邊 {single}%（{t_txt}）｜{br_txt}"
               + ("｜⚠資料不全(週末/盤前空窗)視同不可交易" if data_bad else ""))
    now = datetime.datetime.now(TPE).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "summary": summary, "generated": now,
        "riskoff": {"score": ro, "label": r_txt, "stress": bool(stress), "data_bad": bool(data_bad)},
        "intraday": {"single": single, "chop": chop, "label": t_txt},
        "breadth": {"text": br_txt, "up": up, "dn": dn, "nn": nn},
        "risk_rows": risk_rows, "trend_rows": trend_rows, "etf": etf,
        "lights": lights_out, "binance": binance,
        "movers_up": mv(d.get("movers_up")), "movers_dn": mv(d.get("movers_dn")),
        "movers24_up": mv(d.get("movers24_up")), "movers24_dn": mv(d.get("movers24_dn")),
        "fed": fed_scan(FED_HOURS),  # /dailyecreport 嵌入用:{ok, items:[{time,who,tone,title,src}]}
        "credit": credit_scan(),     # /dailyecreport 嵌入用:{ok, hy, ig, hyg, jnk, lamp:{tok,label,why}}
        "signal_strip": signal_strip(d, credit_scan()),  # 三訊號綜合狀態:{vix,credit,flush,overall}
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--theme", default=DEFAULT_THEME, choices=list(THEMES))
    ap.add_argument("--all", action="store_true", help="一次產出 3 種主題檔(挑風格用)")
    ap.add_argument("--catalyst", default="")
    ap.add_argument("--out", default=None)
    ap.add_argument("--embed-json", action="store_true",
                    help="輸出 {summary,html,generated} JSON 供 dailyecreport 報告嵌入(不寫檔)")
    a = ap.parse_args()
    if getattr(a, "embed_json", False):
        # /dailyecreport 嵌入用：呼叫共用 function 取結構化資料並印出（報告流程亦可直接 import 本 function）。
        print(json.dumps(dashboard_payload(a.catalyst.strip()), ensure_ascii=False))
        return
    print("抓取資料中…", file=sys.stderr)
    d = collect(a.catalyst.strip())
    riskoff, rsub, coverage, stress = score_riskoff(d)
    trend, tsub, gap = score_trend(d)
    lts, data_bad, deadcat = lights(riskoff, trend, coverage, d)
    base = os.path.dirname(os.path.abspath(__file__))
    themes = list(THEMES) if a.all else [a.theme]
    first = None
    for th in themes:
        html = render(d, riskoff, rsub, coverage, trend, tsub, gap, lts, data_bad, deadcat, stress, th)
        out = a.out if (a.out and not a.all) else os.path.join(base, f"strategic_dashboard{'_'+th if a.all else ''}.html")
        with open(out, "w", encoding="utf-8") as _fh:
            _fh.write(html)
        first = first or out
        print(f"[{th}] → {out}")
    print(f"Risk-Off: {ro if (ro:=(f'{riskoff:.0f}' if riskoff is not None else 'N/A')) else ''} (覆蓋 {coverage*100:.0f}%)" + ("  ⚠資料不全" if data_bad else ""))
    print(f"日內大單邊機率: {trend:.0f}%" if trend is not None else "日內: N/A")
    for n, t, tok, w in lts: print(f"  {n}: {t}")
    if a.open:
        import webbrowser; webbrowser.open("file://" + first)

if __name__ == "__main__":
    main()
