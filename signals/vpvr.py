"""vpvr.py — 純標準庫 Volume Profile Visible Range（價量分布/籌碼區），零第三方相依。

比 radar.py 內建的「近似 POC/VAH/VAL」更完整：輸出整條價量直方圖 + POC + 70% Value Area
+ HVN/LVN（高/低量節點）。用於支撐/壓力區判讀（尤其 SOXX 等無幣安永續者可餵 Yahoo OHLCV）。

方法（業界標準 VPVR 近似）：
  - 在 [最低低點, 最高高點] 的可視範圍切 N 個等寬價格 bin。
  - 每根 K 線的「成交量」平均分配到它 [low, high] 掃過的所有 bin（標準等分法）。
  - POC = 成交量最大的 bin（最常被接受的價格 = 最強磁吸/支撐壓力）。
  - Value Area = 由 POC 向上下較大量側逐格擴張，直到累積量達 va_pct(預設 70%)；
    VAH/VAL = 該區最高/最低 bin 的上下緣。
  - HVN = 區域量能高峰(局部極大且≥均量)；LVN = 區域量能低谷(局部極小且≤均量)，常為快速穿越帶。

API：
  vpvr(highs, lows, closes, volumes, bins=24, va_pct=0.70) -> dict
      {poc, vah, val, bin_width, total_vol, profile:[(lo,hi,vol)], hvn:[price...], lvn:[price...]}
  suggest_bins(highs, lows) -> int        依 ATR 自動建議 bin 數（bin 寬≈0.5×ATR，夾 20–60）
  sr_zones(res, price) -> {support:[(price,kind)...], resistance:[...], gaps:[(price,'LVN')...]}
      相對現價的支撐/壓力分區（kind∈POC/VAH/VAL/HVN，近→遠排序）；成交量密集＝均值回歸磁吸，
      只在平衡盤穩健、趨勢盤會棄守，須配趨勢閘門（詳見函式 docstring）。
  fetch_binance_ohlcv(symbol, interval="1d", limit=180, use_spot=False) -> (H,L,C,V)
  summary_text(res, price=None) / summary_html(res, price=None)  便利輸出（給 price 才列 S/R 分區）
  CLI: python3 vpvr.py BTCUSDT [--spot] [--interval 1d] [--limit 180] [--bins 0=自動] [--html]

記憶體/效能：O(bars × bins)；純 list/float；不修改輸入；空/退化輸入安全回 None 欄位。
回測未做＝客觀底稿、非進場依據。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request


def vpvr(highs, lows, closes, volumes, bins=24, va_pct=0.70):
    n = len(closes)
    if not (len(highs) == len(lows) == len(volumes) == n) :
        raise ValueError("highs/lows/closes/volumes 長度必須一致")
    if n == 0:
        return {"poc": None, "vah": None, "val": None, "bin_width": None,
                "total_vol": 0.0, "profile": [], "hvn": [], "lvn": []}
    lo = min(lows)
    hi = max(highs)
    if hi <= lo:   # 全平 → 單一價格
        tv = float(sum(volumes))
        return {"poc": lo, "vah": lo, "val": lo, "bin_width": 0.0,
                "total_vol": tv, "profile": [(lo, hi, tv)], "hvn": [lo], "lvn": []}
    bins = max(1, int(bins))
    w = (hi - lo) / bins
    vol = [0.0] * bins

    def bin_of(price):
        idx = int((price - lo) / w)
        return 0 if idx < 0 else (bins - 1 if idx >= bins else idx)

    # 每根 K 線的量平均分配到它掃過的 bin
    for i in range(n):
        b_lo = bin_of(lows[i])
        b_hi = bin_of(highs[i])
        span = b_hi - b_lo + 1
        share = float(volumes[i]) / span
        for b in range(b_lo, b_hi + 1):
            vol[b] += share

    total = sum(vol)
    profile = [(lo + i * w, lo + (i + 1) * w, vol[i]) for i in range(bins)]

    # POC
    poc_idx = max(range(bins), key=lambda i: vol[i])
    poc = lo + (poc_idx + 0.5) * w

    # Value Area：由 POC 向較大量側擴張到 va_pct
    lo_i = hi_i = poc_idx
    acc = vol[poc_idx]
    target = total * va_pct
    while acc < target and (lo_i > 0 or hi_i < bins - 1):
        below = vol[lo_i - 1] if lo_i > 0 else -1.0
        above = vol[hi_i + 1] if hi_i < bins - 1 else -1.0
        if above >= below:
            hi_i += 1
            acc += vol[hi_i]
        else:
            lo_i -= 1
            acc += vol[lo_i]
    val = lo + lo_i * w
    vah = lo + (hi_i + 1) * w

    # HVN/LVN：局部極值 + 均量門檻
    mean = total / bins if bins else 0.0
    hvn, lvn = [], []
    for i in range(bins):
        left = vol[i - 1] if i > 0 else -1.0
        right = vol[i + 1] if i < bins - 1 else -1.0
        center = lo + (i + 0.5) * w
        if vol[i] >= left and vol[i] >= right and vol[i] >= mean:
            hvn.append(center)
        if vol[i] <= left and vol[i] <= right and vol[i] <= mean:
            lvn.append(center)

    return {"poc": poc, "vah": vah, "val": val, "bin_width": w,
            "total_vol": total, "profile": profile, "hvn": hvn, "lvn": lvn}


def fetch_binance_ohlcv(symbol, interval="1d", limit=180, use_spot=False):
    base = "https://api.binance.com/api/v3" if use_spot else "https://fapi.binance.com/fapi/v1"
    url = f"{base}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    d = json.load(urllib.request.urlopen(url, timeout=12))
    H = [float(k[2]) for k in d]
    L = [float(k[3]) for k in d]
    C = [float(k[4]) for k in d]
    V = [float(k[5]) for k in d]
    return H, L, C, V


def suggest_bins(highs, lows, lo_cap=20, hi_cap=60):
    """依「bin 寬 ≈ 0.5×ATR」自動建議 bin 數（ATR 以均 (high-low) 近似），夾在 [lo_cap, hi_cap]。
    太多 bin→雜訊、每格都像節點；太少→糊成一團。配上標的波動才「準」。空輸入回 24。"""
    if not highs or not lows:
        return 24
    rng = max(highs) - min(lows)
    if rng <= 0:
        return 1
    atr = sum(h - l for h, l in zip(highs, lows)) / len(highs)
    if atr <= 0:
        return 24
    return max(lo_cap, min(hi_cap, round(rng / (0.5 * atr))))


def sr_zones(res, price, max_each=4):
    """從 VPVR 結果萃取『相對現價』的支撐/壓力區。
    回 {support:[(price,kind)...], resistance:[(price,kind)...], gaps:[(price,'LVN')...]}
      - kind ∈ {POC, VAH, VAL, HVN}；POC=最大成交量節點（最強磁吸）。
      - resistance 由近到遠（現價上方由低到高）；support 由近到遠（現價下方由高到低）。
      - gaps=LVN 真空帶（快速穿越，不是 S/R）。
    ★這是『成交量密集＝均值回歸磁吸』的 S/R，只在平衡/區間盤穩健；強趨勢盤會直接棄守，需配趨勢閘門。
    空/退化輸入或無現價 → 空清單。"""
    out = {"support": [], "resistance": [], "gaps": []}
    if res.get("poc") is None or price is None:
        return out
    cand = [(res.get("poc"), "POC"), (res.get("vah"), "VAH"), (res.get("val"), "VAL")]
    cand += [(h, "HVN") for h in (res.get("hvn") or [])]
    tol = (res.get("bin_width") or 0.0) * 0.5  # 去重容差（同一價帶只留先出現的強標籤）
    uniq = []
    for p, k in cand:
        if p is None:
            continue
        if any(abs(p - q) <= tol for q, _ in uniq):
            continue
        uniq.append((p, k))
    for p, k in uniq:
        if p > price:
            out["resistance"].append((p, k))
        elif p < price:
            out["support"].append((p, k))
    out["resistance"].sort(key=lambda x: x[0])                 # 近→遠
    out["support"].sort(key=lambda x: x[0], reverse=True)      # 近→遠
    out["resistance"] = out["resistance"][:max_each]
    out["support"] = out["support"][:max_each]
    out["gaps"] = [(p, "LVN") for p in (res.get("lvn") or [])]
    return out


def _fmt(p):
    if p is None:
        return "NA"
    return f"{p:,.2f}" if p >= 100 else f"{p:.4f}"


def _zones_line(res, price):
    """把 sr_zones 轉成一行『支撐 / 壓力』字串（給 summary 用）。"""
    z = sr_zones(res, price)
    sup = "、".join(f"{_fmt(p)}({k})" for p, k in z["support"]) or "—"
    rst = "、".join(f"{_fmt(p)}({k})" for p, k in z["resistance"]) or "—"
    out = [f"壓力區（上）：{rst}", f"支撐區（下）：{sup}"]
    if z["gaps"]:
        out.append("真空帶 LVN（快穿）：" + "、".join(_fmt(p) for p, _ in z["gaps"][:6]))
    return out


def summary_text(res, price=None):
    if res["poc"] is None:
        return "VPVR：無資料"
    lines = [f"POC {_fmt(res['poc'])} ｜ VA {_fmt(res['val'])}–{_fmt(res['vah'])}（70%）"]
    if price is not None:
        lines += _zones_line(res, price)
        zone = ("VA 之上（偏多/壓力在 VAH）" if price > res["vah"]
                else "VA 之下（偏空/支撐在 VAL）" if price < res["val"]
                else "VA 之內（區間，POC 為多空分界）")
        lines.append(f"現價 {_fmt(price)} 位於 {zone}（S/R＝均值回歸磁吸，趨勢盤會棄守，需配趨勢閘門）")
    else:
        if res["hvn"]:
            lines.append("HVN（高量節點/支撐壓力）：" + "、".join(_fmt(p) for p in res["hvn"][:6]))
        if res["lvn"]:
            lines.append("LVN（低量節點/快速穿越）：" + "、".join(_fmt(p) for p in res["lvn"][:6]))
    return "\n".join(lines)


def summary_html(res, price=None):
    body = summary_text(res, price).replace("\n", "<br>")
    return f'<div class="vpvr-box">🧱 VPVR 籌碼區<br>{body}</div>'


def _main(argv):
    ap = argparse.ArgumentParser(description="VPVR 價量分布")
    ap.add_argument("symbol")
    ap.add_argument("--spot", action="store_true")
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--limit", type=int, default=180)
    ap.add_argument("--bins", type=int, default=0, help="0=依 ATR 自動（建議）；>0 手動覆蓋")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args(argv)
    H, L, C, V = fetch_binance_ohlcv(a.symbol, a.interval, a.limit, a.spot)
    bins = a.bins if a.bins and a.bins > 0 else suggest_bins(H, L)
    res = vpvr(H, L, C, V, bins=bins)
    price = C[-1] if C else None
    print(summary_html(res, price) if a.html else f"[{a.symbol} VPVR {a.interval}×{a.limit}]\n" + summary_text(res, price))


if __name__ == "__main__":
    _main(sys.argv[1:])
