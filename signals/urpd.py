"""urpd.py — BTC 成本分布代理（URPD proxy），純標準庫，重用 vpvr 核心。

URPD（UTXO Realized Price Distribution）原義 = 每個價位有多少 BTC「最後一次鏈上移動」，
是 crypto 最硬的籌碼圖（真正的持幣成本分布）。真 URPD 需全 UTXO 集 + 逐筆成本，
只有 Glassnode / CryptoQuant / CoinGlass 等鏈上資料商提供（多為付費）。

★本工具是「交易所成交量成本代理」，不是真鏈上 URPD：
  在一段視窗上跑 Volume Profile（vpvr 核心），把成交量在價位上的堆積當成
  「幣多半在哪些價位換手 / 成本聚集」的代理。它捕捉交易所成交的成本簇，
  與鏈上 UTXO 成本分布相關但不等同（缺冷錢包長期未動的幣、含高頻重複換手）。
  真鏈上 URPD 請用 Glassnode「URPD」圖 / CoinGlass。本工具用於無鏈上資料時的結構底稿。

★紅隊校正（2026-10-24）後的兩個關鍵設計：
  1. 用 **quote volume（USD 名目，kline[7]）** 而非 base(BTC) 量加權——否則早年廉價幣的巨大 BTC
     周轉會把 POC 機械釘在週期低點，嚴重失真。
  2. **預設只看當前週期短窗（weekly×200≈近 ~4 年）**，而非全歷史——全歷史線性 bin 在
     3k→80k 的拋物線上會把 POC/HVN 壓到週期底、並讓 below% 恆趨近 100%。要看全歷史請自行加大 --limit。
  另提供 **--log**（對數價格 bin），在跨越多倍數的長視窗上讓 bin 分布更公平。

★below%/above%（獲利/套牢供給代理）的硬性 caveat：
  它是「本視窗內、成交量-時間加權」的現價上下占比，**不是真實持幣成本分布**。
  對長期上升資產，現價接近 ATH 時 below% 會機械趨近 100%（趨勢綁架，換 log bin 也救不了），
  **不可與 Glassnode URPD 的「供給在獲利 %」類比**。只在「現價位於視窗中段」時較有參考性。

在 VPVR 之上額外給出 URPD 式判讀：
  - 成本簇（cost-basis clusters）= HVN = 籌碼密集價帶（強支撐/壓力）。
  - 現價相對最大成本簇（POC）的位置 → 多空分界。
  - below%/above%（見上方 caveat）。

資料源：Binance SPOT 週線（`api.binance.com`），用 quote volume 加權。

API：
  urpd(highs, lows, closes, quote_vols, bins=50, price=None, log=False) -> dict
      繼承 vpvr 全部欄位，另加：{clusters, below_pct, above_pct, poc_side, price}
  fetch_binance_history(symbol, interval="1w", limit=200) -> (H, L, C, QV, span)
      QV=quote volume(USD)；span=(first_date, last_date) 字串
  summary_text(res, span=None) / summary_html(res, span=None)
  CLI: python3 urpd.py BTCUSDT [--interval 1w] [--limit 200] [--bins 50] [--log] [--html]

注意：成本分布代理 ≠ 進場訊號；Volume Profile 回測未做，為客觀結構底稿。
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
import urllib.request

import vpvr as _vpvr


def urpd(highs, lows, closes, quote_vols, bins=50, price=None, log=False):
    """在視窗上跑 VPVR（quote-volume 加權），補上 URPD 式判讀。
    log=True 時在對數價格空間切 bin（跨多倍數視窗較公平），回傳價位會還原回線性空間。
    price 預設取 closes[-1]。空輸入安全回 None 欄位。"""
    if log and closes and all(x > 0 for x in highs) and all(x > 0 for x in lows):
        lh = [math.log(x) for x in highs]
        ll = [math.log(x) for x in lows]
        lc = [math.log(x) for x in closes]
        res = _vpvr.vpvr(lh, ll, lc, quote_vols, bins=bins)
        _exp_in_place(res)
    else:
        res = _vpvr.vpvr(highs, lows, closes, quote_vols, bins=bins)

    res["price"] = price if price is not None else (closes[-1] if closes else None)
    res["clusters"] = list(res.get("hvn") or [])
    res["below_pct"] = None
    res["above_pct"] = None
    res["poc_side"] = None

    p = res["price"]
    prof = res.get("profile") or []
    total = res.get("total_vol") or 0.0
    if p is not None and total > 0:
        below = sum(v for lo, hi, v in prof if (lo + hi) / 2.0 <= p)
        res["below_pct"] = below / total * 100.0
        res["above_pct"] = 100.0 - res["below_pct"]
    if p is not None and res.get("poc") is not None:
        res["poc_side"] = "above" if p > res["poc"] else "below" if p < res["poc"] else "at"
    return res


def _exp_in_place(res):
    """把對數空間跑出來的價位欄位還原回線性價格。"""
    def ex(x):
        return math.exp(x) if x is not None else None
    for k in ("poc", "vah", "val"):
        res[k] = ex(res[k])
    res["hvn"] = [ex(x) for x in res.get("hvn") or []]
    res["lvn"] = [ex(x) for x in res.get("lvn") or []]
    res["profile"] = [(ex(lo), ex(hi), v) for lo, hi, v in res.get("profile") or []]
    res["bin_width"] = None  # 對數空間等寬 → 線性空間非等寬，無單一值


def fetch_binance_history(symbol, interval="1w", limit=200):
    """抓 Binance SPOT K 線，回 (H, L, C, QuoteVolume, span)。
    QuoteVolume=kline[7]（USD 名目成交額）；span=(首根, 末根) 日期字串。"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={int(limit)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))
    H = [float(k[2]) for k in d]
    L = [float(k[3]) for k in d]
    C = [float(k[4]) for k in d]
    QV = [float(k[7]) for k in d]  # quote asset volume (USD)
    span = None
    if d:
        f = datetime.datetime.utcfromtimestamp(d[0][0] / 1000).strftime("%Y-%m-%d")
        l = datetime.datetime.utcfromtimestamp(d[-1][0] / 1000).strftime("%Y-%m-%d")
        span = (f, l)
    return H, L, C, QV, span


def summary_text(res, span=None):
    if res.get("poc") is None:
        return "URPD 代理：無資料"
    f = _vpvr._fmt
    p = res.get("price")
    win = f"（視窗 {span[0]}→{span[1]}）" if span else ""
    lines = [
        f"⚠ 交易所成交量(USD)成本代理{win}；非鏈上真 URPD，真鏈上請用 Glassnode/CoinGlass",
        f"最大成本簇 POC {f(res['poc'])} ｜ 價值區 VA {f(res['val'])}–{f(res['vah'])}（70%）",
    ]
    if p is not None:
        lines += _vpvr._zones_line(res, p)
    elif res["clusters"]:
        lines.append("成本密集帶（HVN/籌碼簇）：" + "、".join(f(x) for x in res["clusters"][:8]))
    if res.get("poc_side"):
        side = {"above": "現價在最大成本簇之上（成本簇為支撐，偏多結構）",
                "below": "現價在最大成本簇之下（成本簇為壓力，偏空結構）",
                "at": "現價貼齊最大成本簇（多空分界，易震盪）"}[res["poc_side"]]
        lines.append(side)
    if res.get("below_pct") is not None and p is not None:
        lines.append(
            f"現價 {f(p)}：本視窗約 {res['below_pct']:.0f}% 成交量在下方、{res['above_pct']:.0f}% 在上方"
            "　⚠此為『視窗內成交量-時間加權』非真實持幣成本；近 ATH 時下方%會機械趨近 100%，"
            "不可當『供給在獲利%』、不可與鏈上 URPD 類比")
    return "\n".join(lines)


def summary_html(res, span=None):
    body = summary_text(res, span).replace("\n", "<br>")
    return f'<div class="urpd-box">🪙 BTC 成本分布代理（URPD proxy）<br>{body}</div>'


def _main(argv):
    ap = argparse.ArgumentParser(description="BTC 成本分布代理（URPD proxy，交易所 Volume Profile）")
    ap.add_argument("symbol", nargs="?", default="BTCUSDT")
    ap.add_argument("--interval", default="1w")
    ap.add_argument("--limit", type=int, default=200, help="K 線根數（預設 200 週≈當前週期；加大看更長歷史）")
    ap.add_argument("--bins", type=int, default=50)
    ap.add_argument("--log", action="store_true", help="對數價格 bin（跨多倍數長視窗較公平）")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args(argv)
    H, L, C, QV, span = fetch_binance_history(a.symbol, a.interval, a.limit)
    res = urpd(H, L, C, QV, bins=a.bins, log=a.log)
    print(summary_html(res, span) if a.html
          else f"[{a.symbol} URPD 代理 {a.interval}×{len(C)}{' log-bin' if a.log else ''}]\n"
               + summary_text(res, span))


if __name__ == "__main__":
    _main(sys.argv[1:])
