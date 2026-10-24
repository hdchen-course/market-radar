"""options_maxpain.py — 純標準庫股票選擇權籌碼分布（Max Pain / OI 牆 / PCR / Gamma 牆），零第三方相依。

用途：股票（如 MSTR）沒有鏈上籌碼，選擇權 open interest 分布是最接近「籌碼/持倉分布」的資料。
本工具從 CBOE 延遲報價（免認證、含 OI/volume/iv/gamma/delta）算出：
  - Max Pain：到期時讓選擇權買方「總賠付最小」的結算價 = 常被引為到期磁吸(pin)價。
  - OI 牆：call OI 最大的履約價(上方壓力/磁吸)、put OI 最大的履約價(下方支撐)。
  - PCR：put/call 比（OI 與 volume 兩種），情緒/避險代理。
  - Gamma 牆 & 淨 GEX（近似）：做市商 gamma 曝險集中價位 + 正/負 gamma regime 粗判。

★誠實鐵則：
  - CBOE 報價為「延遲」資料（非即時），且 OI 為前一交易日結算值（T+1）；只反映到報價日的持倉結構，
    不保證抓到即時換手。做決策前以此為「結構底稿」，非進場訊號。
  - Max Pain 是機械計算值，不是預測；它假設「價格傾向往買方最痛處收斂」只是經驗傾向，常被總經/催化蓋過。
  - 淨 GEX 用常見近似（call gamma 記正、put gamma 記負，× OI×100×S²×0.01），
    做市商持倉方向其實未知 → 只當「量級/集中價位」參考，不當精確美元值。

資料源：https://cdn.cboe.com/api/global/delayed_quotes/options/{SYMBOL}.json （需跟隨 307 重導）

API：
  parse_occ(sym) -> (root, 'YYYY-MM-DD', 'C'|'P', strike_float)
  fetch_cboe(symbol) -> (spot_float, rows)              rows=[{expiry,type,strike,oi,vol,gamma,delta}...]
  group_by_expiry(rows) -> {expiry: [row...]}
  max_pain(rows) -> strike_float | None                 rows 須為單一到期
  oi_walls(rows, top=3) -> {'call':[(strike,oi)...], 'put':[(strike,oi)...]}
  pcr(rows) -> {'oi': float|None, 'vol': float|None}
  gex(rows, spot) -> {'net': float, 'call_wall': (strike,val)|None, 'put_wall': (strike,val)|None}
  analyze(spot, rows, expiries=3) -> dict（近月彙總 + 逐到期）
  summary_text(res) / summary_html(res)
  CLI: python3 options_maxpain.py MSTR [--expiries 3] [--html]

記憶體/效能：O(rows + strikes²) per expiry（strikes 數百，瞬間完成）；純 list/dict/float；不修改輸入。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

_OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def parse_occ(sym):
    """拆 OCC 選擇權符號，如 'MSTR270115P00620000' -> ('MSTR','2027-01-15','P',620.0)。不合法回 None。"""
    m = _OCC.match(sym)
    if not m:
        return None
    root, ymd, cp, strike8 = m.groups()
    yy, mm, dd = int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6])
    year = 2000 + yy  # OCC 用兩位年；本資料皆 21 世紀
    return root, f"{year:04d}-{mm:02d}-{dd:02d}", cp, int(strike8) / 1000.0


def fetch_cboe(symbol):
    """抓 CBOE 延遲選擇權鏈。回 (spot, rows)。網路/解析失敗拋例外交由呼叫端處理。"""
    url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol.upper()}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))
    data = d["data"]
    spot = data.get("current_price") or data.get("close")
    spot = float(spot) if spot is not None else None
    rows = []
    for o in data.get("options", []):
        p = parse_occ(o.get("option", ""))
        if not p:
            continue
        _root, expiry, cp, strike = p
        rows.append({
            "expiry": expiry,
            "type": cp,
            "strike": strike,
            "oi": float(o.get("open_interest") or 0.0),
            "vol": float(o.get("volume") or 0.0),
            "gamma": float(o.get("gamma") or 0.0),
            "delta": float(o.get("delta") or 0.0),
        })
    return spot, rows


def group_by_expiry(rows):
    out = {}
    for r in rows:
        out.setdefault(r["expiry"], []).append(r)
    return out


def max_pain(rows):
    """單一到期的 max pain 履約價：讓所有未平倉選擇權買方『總內在價值賠付』最小的結算價。
    payout(K) = Σ_call OI×max(K−strike,0) + Σ_put OI×max(strike−K,0)，取最小的 K（限列出的履約價）。
    無資料或全 OI 為 0 回 None。"""
    strikes = sorted({r["strike"] for r in rows})
    if not strikes:
        return None
    calls = [(r["strike"], r["oi"]) for r in rows if r["type"] == "C" and r["oi"] > 0]
    puts = [(r["strike"], r["oi"]) for r in rows if r["type"] == "P" and r["oi"] > 0]
    if not calls and not puts:
        return None
    best_k, best_pay = None, None
    for K in strikes:
        pay = 0.0
        for s, oi in calls:
            if K > s:
                pay += oi * (K - s)
        for s, oi in puts:
            if s > K:
                pay += oi * (s - K)
        if best_pay is None or pay < best_pay:
            best_pay, best_k = pay, K
    return best_k


def oi_walls(rows, top=3):
    """各履約價 call / put OI，取 OI 最大的前 top 檔。call 牆=上方壓力/磁吸，put 牆=下方支撐。"""
    call_oi, put_oi = {}, {}
    for r in rows:
        tgt = call_oi if r["type"] == "C" else put_oi
        tgt[r["strike"]] = tgt.get(r["strike"], 0.0) + r["oi"]
    def topn(d):
        return sorted(((k, v) for k, v in d.items() if v > 0), key=lambda kv: kv[1], reverse=True)[:top]
    return {"call": topn(call_oi), "put": topn(put_oi)}


def pcr(rows):
    """Put/Call 比：OI 與 volume 兩種。>1 偏避險/看空持倉，<1 偏看多。分母 0 回 None。"""
    co = sum(r["oi"] for r in rows if r["type"] == "C")
    po = sum(r["oi"] for r in rows if r["type"] == "P")
    cv = sum(r["vol"] for r in rows if r["type"] == "C")
    pv = sum(r["vol"] for r in rows if r["type"] == "P")
    return {"oi": (po / co if co > 0 else None),
            "vol": (pv / cv if cv > 0 else None)}


def gex(rows, spot):
    """淨 Gamma 曝險(近似) + gamma 牆。call gamma 記正、put gamma 記負，
    每檔貢獻 = γ × OI × 100 × spot² × 0.01（1% 位移的 delta 變動金額量級）。
    net>0 多半 = 正 gamma（做市商壓波動、價格黏著）；net<0 = 負 gamma（追漲殺跌放大波動）。
    call_wall/put_wall = |gamma×OI| 最大的履約價（做市商對沖最密集處，常為磁吸/轉折）。
    spot 不可用時回零值結構。"""
    if not spot or spot <= 0:
        return {"net": 0.0, "call_wall": None, "put_wall": None}
    k = 100.0 * spot * spot * 0.01
    net = 0.0
    call_g, put_g = {}, {}
    for r in rows:
        contrib = r["gamma"] * r["oi"] * k
        if r["type"] == "C":
            net += contrib
            call_g[r["strike"]] = call_g.get(r["strike"], 0.0) + r["gamma"] * r["oi"]
        else:
            net -= contrib
            put_g[r["strike"]] = put_g.get(r["strike"], 0.0) + r["gamma"] * r["oi"]
    def peak(d):
        d = {s: v for s, v in d.items() if v > 0}
        if not d:
            return None
        s = max(d, key=lambda x: d[x])
        return (s, d[s])
    return {"net": net, "call_wall": peak(call_g), "put_wall": peak(put_g)}


def analyze(spot, rows, expiries=3):
    """彙總最近 `expiries` 個到期：逐到期 max_pain/walls/pcr/gex + 近月合併彙總。"""
    by = group_by_expiry(rows)
    exps = sorted(by.keys())[:max(1, expiries)]
    per = []
    merged = []
    for e in exps:
        er = by[e]
        merged.extend(er)
        per.append({
            "expiry": e,
            "max_pain": max_pain(er),
            "walls": oi_walls(er),
            "pcr": pcr(er),
            "gex": gex(er, spot),
            "n": len(er),
        })
    return {
        "spot": spot,
        "expiries": exps,
        # 頭條磁吸價用「最近到期」單一到期（跨到期混算的 max_pain 對任一到期都不成立）
        "front_expiry": exps[0] if exps else None,
        "front_max_pain": per[0]["max_pain"] if per else None,
        "near": {
            # walls/pcr/gex 跨到期合算有意義（總持倉結構）；max_pain 則標明為合算參考
            "max_pain_merged": max_pain(merged),
            "walls": oi_walls(merged),
            "pcr": pcr(merged),
            "gex": gex(merged, spot),
        },
        "per_expiry": per,
    }


def _f(p):
    return "NA" if p is None else f"{p:,.2f}"


def _walls_str(w):
    c = "、".join(f"{_f(s)}(OI {oi:,.0f})" for s, oi in w["call"]) or "—"
    p = "、".join(f"{_f(s)}(OI {oi:,.0f})" for s, oi in w["put"]) or "—"
    return c, p


def summary_text(res):
    if res["spot"] is None and not res["expiries"]:
        return "選擇權：無資料"
    n = res["near"]
    cwall, pwall = _walls_str(n["walls"])
    g = n["gex"]
    oi, vol = n["pcr"]["oi"], n["pcr"]["vol"]
    pcr_str = (f"  PCR  OI {oi:.2f} ｜ Vol {vol:.2f}" if oi is not None and vol is not None
               else f"  PCR  OI {oi if oi is None else f'{oi:.2f}'} ｜ Vol {vol if vol is None else f'{vol:.2f}'}")
    lines = [
        f"現價 {_f(res['spot'])}（CBOE 延遲；OI 為 T+1 結算，結構底稿非進場訊號）",
        f"最近到期 {res['front_expiry']} Max Pain(磁吸價) {_f(res['front_max_pain'])}",
        f"跨 {len(res['expiries'])} 個到期合算（{', '.join(res['expiries'])}）：",
        f"  Max Pain(合算參考，非單一到期) {_f(n['max_pain_merged'])}",
        f"  Call 牆(壓力) {cwall}",
        f"  Put 牆(支撐) {pwall}",
        pcr_str,
    ]
    regime = "正γ(壓波動/黏著)" if g["net"] > 0 else "負γ(放大波動/追漲殺跌)" if g["net"] < 0 else "中性"
    gc = f"{_f(g['call_wall'][0])}" if g["call_wall"] else "—"
    gp = f"{_f(g['put_wall'][0])}" if g["put_wall"] else "—"
    lines.append(f"  Gamma 近似 {regime}；γ 牆 call {gc} / put {gp}"
                 "（假設做市商 long call/short put；量級參考、方向無法驗證）")
    mp = res["front_max_pain"]
    if res["spot"] is not None and mp:
        diff = (res["spot"] - mp) / mp * 100
        if abs(diff) < 0.05:
            lines.append(f"  現價 vs 最近到期 Max Pain：貼齊（{_f(mp)}，到期前多空分界）")
        else:
            lines.append(f"  現價 vs 最近到期 Max Pain：{'高於' if diff > 0 else '低於'} {abs(diff):.1f}%"
                         f"（{'若收斂有向下磁吸傾向' if diff > 0 else '若收斂有向上磁吸傾向'}，僅經驗傾向）")
    return "\n".join(lines)


def summary_html(res):
    body = summary_text(res).replace("\n", "<br>")
    return f'<div class="opt-box">🎯 選擇權籌碼（Max Pain / OI 牆 / PCR / Gamma）<br>{body}</div>'


def _main(argv):
    ap = argparse.ArgumentParser(description="股票選擇權籌碼分布（Max Pain/OI 牆/PCR/Gamma）")
    ap.add_argument("symbol")
    ap.add_argument("--expiries", type=int, default=3, help="彙總最近幾個到期（預設 3）")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args(argv)
    spot, rows = fetch_cboe(a.symbol)
    res = analyze(spot, rows, a.expiries)
    try:
        import runlog
        runlog.stamp("options", {"symbol": a.symbol.upper(), "spot": spot,
                                 "front_max_pain": res.get("front_max_pain")})
    except Exception:
        pass
    print(summary_html(res) if a.html
          else f"[{a.symbol.upper()} 選擇權籌碼]\n" + summary_text(res))


if __name__ == "__main__":
    _main(sys.argv[1:])
