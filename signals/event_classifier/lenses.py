#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lenses.py — 階段2 對抗鏡頭層

不投票、不生方向、不生敘事。對「一個已存在的訊號/因果宣稱」問攻擊性問題、輸出紅旗。
方向仍由訊號 + 使用者盤感決定。

兩級分艙(對抗 reviewer 攻擊#7 的要求):
  A 艙 規則化鏡頭(紅旗是被計算出來的統計量,可寫入程式化欄位):
    L1 做市商/籌碼   — COT 分位:漲是真買還是逼空?
    L2 量化/過擬合   — 這訊號去重後還顯著?單一年代撐的?(讀 event_classifier 回測結果)
    L3 技術/插針     — 收盤站穩還是盤中插針收回?量能配合?
    L4 總經反向      — 敘事與 DXY/殖利率方向矛盾嗎?量級對得上嗎?
  B 艙 判讀鏡頭(裁決是主觀判斷,只輸出「該問的攻擊問題」,不自動下 CONFIRMED/REFUTED):
    L5 商品實體 / L6 地緣 / L7 催化溯源

  + 散戶陷阱/心理層 — 對照使用者本人老毛病(參照點/攤平/確認偏誤)打紅旗。

用法:
    .venv/bin/python event_classifier/lenses.py --asset SI=F --claim-dir up --note "白銀突破$65"
"""
import sys, os, json, urllib.request, urllib.parse, argparse, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SIGNALS = os.path.dirname(HERE)
sys.path.insert(0, SIGNALS)
from silver_daily import fetch_yf, fetch_cot   # 複用免費抓取


# ---------- 帶量價抓取(技術鏡頭用) ----------
def fetch_ohlcv(symbol, days=60):
    import time
    p2 = int(time.time()); p1 = p2 - days * 86400
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    r = d["chart"]["result"][0]
    ts = r["timestamp"]; q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"o": q["open"], "h": q["high"], "l": q["low"],
                       "c": q["close"], "v": q["volume"]},
                      index=[pd.Timestamp(t, unit="s").normalize() for t in ts]).dropna()
    return df


# ---------- A 艙:規則化鏡頭 ----------
def lens_positioning(asset):
    """L1 籌碼:僅白銀有 COT。漲勢是否由空單高位回補推動(逼空,燃料有限)。"""
    flags = []
    if "SI" not in asset.upper() and "XAG" not in asset.upper():
        return {"lens": "L1籌碼", "applicable": False,
                "note": "非白銀,COT 不適用(晶片股無對應投機持倉公開週報)"}
    try:
        cot = fetch_cot()
    except Exception as e:
        return {"lens": "L1籌碼", "applicable": False, "note": f"COT 抓取失敗:{e}"}
    p26, p260 = cot["short_pct26"], cot["short_pct260"]
    if p26 is not None and p26 >= 80 and p260 is not None and p260 < 30:
        flags.append(f"空單26週分位{p26}%高、5年僅{p260}%=帶寬假象,燃料池不大→軋空續航有限")
    return {"lens": "L1籌碼", "applicable": True,
            "data": {"short_pct26": p26, "short_pct52": cot["short_pct52"],
                     "short_pct260": p260, "short_range26": cot["short_range26"], "date": cot["date"]},
            "flags": flags,
            "caveat": "COT 落後約10天,只讀週級結構,不得宣稱抓即時軋空頂底"}


def lens_technical(asset):
    """L3 技術/插針:最後一根日 K 是否收盤站穩,還是長影插針/破位無量。"""
    df = fetch_ohlcv(asset)
    if len(df) < 21:
        return {"lens": "L3技術", "applicable": False, "note": "資料不足"}
    last = df.iloc[-1]
    rng = last["h"] - last["l"]
    body_hi = max(last["o"], last["c"]); body_lo = min(last["o"], last["c"])
    up_wick = (last["h"] - body_hi) / rng if rng > 0 else 0
    dn_wick = (body_lo - last["l"]) / rng if rng > 0 else 0
    vol20 = df["v"].iloc[-21:-1].mean()
    vol_ratio = last["v"] / vol20 if vol20 > 0 else float("nan")
    flags = []
    if up_wick > 0.5:
        flags.append(f"長上影(上影佔全距{up_wick*100:.0f}%)=衝高被壓回,追多留意假突破")
    if dn_wick > 0.5:
        flags.append(f"長下影(下影佔全距{dn_wick*100:.0f}%)=殺低被拉回,追空留意假破位")
    if vol_ratio < 0.7:
        flags.append(f"量能僅20日均{vol_ratio*100:.0f}%=破位/突破無量,續航存疑")
    return {"lens": "L3技術", "applicable": True,
            "data": {"close": round(last["c"], 2), "up_wick_pct": round(up_wick*100, 0),
                     "dn_wick_pct": round(dn_wick*100, 0), "vol_vs_20d": round(vol_ratio, 2)},
            "flags": flags}


def lens_macro_reversal(claim_dir):
    """L4 總經反向:宣稱方向(up/down)與 DXY/殖利率是否矛盾、量級對不對得上。
       claim_dir='up' 指宣稱標的會漲。針對貴金屬:漲若歸因弱美元/降息,DXY 該弱、殖利率該降。"""
    try:
        dxy = fetch_yf("DX-Y.NYB"); tnx = fetch_yf("^TNX")
    except Exception as e:
        return {"lens": "L4總經反向", "applicable": False, "note": f"宏觀抓取失敗:{e}"}
    dxy_chg = (dxy.iloc[-1] / dxy.iloc[-2] - 1) * 100 if len(dxy) >= 2 else float("nan")
    tnx_chg = tnx.iloc[-1] - tnx.iloc[-2] if len(tnx) >= 2 else float("nan")
    flags = []
    # 若宣稱貴金屬漲=弱美元/降息推動,檢查量級與方向
    if claim_dir == "up":
        if dxy_chg > -0.1:
            flags.append(f"DXY 日變動{dxy_chg:+.2f}%(未明顯走弱)→『弱美元推漲』量級/方向對不上,勿當主因")
        if tnx_chg > -0.01:
            flags.append(f"10Y殖利率{tnx_chg:+.3f}(未降/反升)→『降息推漲』與現實矛盾,別跳級成降息啟動")
    return {"lens": "L4總經反向", "applicable": True,
            "data": {"dxy_now": round(dxy.iloc[-1], 2), "dxy_chg_pct": round(dxy_chg, 2),
                     "tnx_now": round(tnx.iloc[-1], 2), "tnx_chg": round(tnx_chg, 3)},
            "flags": flags,
            "caveat": "量級對得上才可歸因(DXY只動0.1-0.5%撐不起金銀±5%)"}


# ---------- B 艙:判讀鏡頭(只輸出攻擊問題,不自動裁決) ----------
B_LENSES = [
    {"lens": "L5商品實體", "ask": "有實體證據嗎?期限結構/庫存/EFP/租賃利率?查對管道嗎(逼倉在倫敦EFP不在COMEX)?",
     "limit": "LBMA/EFP/租賃利率免費即時源不穩→月頻/落後背景,不當即時紅旗,裁決主觀"},
    {"lens": "L6地緣", "ask": "實質升級還是重複舊聲明?誰打誰、幾處、首次還升級?油價量級撐得起定價嗎?",
     "limit": "升級≠買金;市場只對實質升級定價,裁決主觀"},
    {"lens": "L7催化溯源", "ask": "這『原因』有一手來源+時間戳嗎?跨幾管道?單一來源/謠言/媒體共識被當事實?報告發布在價格動之前還之後(領先或跟風)?",
     "limit": "查不到只能寫『暫未查到』不可寫『查無』;裁決主觀,不進程式化欄位"},
]


# ---------- 散戶陷阱 / 心理層(對照使用者老毛病) ----------
def lens_psychology(claim_dir, holding_dir, moved_pct, note):
    """散戶會掉的具名陷阱 + 使用者本人老毛病紅旗。
       holding_dir: 'short'/'long'/None(使用者當前持倉方向)
       moved_pct: 事件標的近期已移動幅度(%),用來判追高/追低。"""
    flags = []
    # 追高殺低
    if moved_pct is not None:
        if claim_dir == "up" and moved_pct > 3:
            flags.append(f"追高陷阱:已漲{moved_pct:+.1f}%才想追多=可能買在情緒高點")
        if claim_dir == "down" and moved_pct < -3:
            flags.append(f"追低陷阱:已跌{moved_pct:+.1f}%才想追空=可能空在半山腰下緣")
    # 確認偏誤:持倉方向與宣稱方向一致
    if holding_dir == "short" and claim_dir == "down":
        flags.append("確認偏誤:你持空、又找『會跌』的理由=只看支持部位的證據,留意反向訊號")
    if holding_dir == "long" and claim_dir == "up":
        flags.append("確認偏誤:你持多、又找『會漲』的理由=同上,別只看利多")
    # 報復性加碼/攤平(使用者記憶中的老毛病)
    if holding_dir and moved_pct is not None and abs(moved_pct) > 2:
        flags.append("加碼攤平陷阱:離成本遠時加碼要押很大才拉均價=風險暴增,別報復性加碼")
    # 參照點情緒(使用者本人)
    flags.append("參照點提醒:浮盈/出場後的波動都不是你的錢,落袋的才是;贏用移動停利、破線認錯別凪、別預設價位接刀")
    return {"lens": "散戶陷阱/心理", "flags": flags}


# ---------- 主流程 ----------
def run(asset="SI=F", claim_dir="up", holding_dir=None, note=""):
    # 近 5 日移動幅度(判追高/追低)
    try:
        s = fetch_yf(asset, days=30)
        moved = (s.iloc[-1] / s.iloc[-6] - 1) * 100 if len(s) >= 6 else None
    except Exception:
        moved = None

    A = [lens_positioning(asset), lens_technical(asset), lens_macro_reversal(claim_dir)]
    psych = lens_psychology(claim_dir, holding_dir, moved, note)

    out = {"asof": str(dt.date.today()), "asset": asset, "claim_dir": claim_dir,
           "holding_dir": holding_dir, "note": note, "moved_5d_pct": round(moved, 1) if moved is not None else None,
           "A_rule_lenses": A, "psychology": psych, "B_judgment_lenses": B_LENSES}
    return out


def render(o):
    L = ["=" * 70,
         f"  對抗鏡頭層 | {o['asset']} | 宣稱方向:{o['claim_dir']} | 近5日動:{o['moved_5d_pct']}%",
         f"  情境:{o['note'] or '(未註明)'}  持倉:{o['holding_dir'] or '無'}",
         "=" * 70,
         "【A 艙 規則化鏡頭 — 紅旗由資料算出,可信】"]
    for lens in o["A_rule_lenses"]:
        L.append(f"\n▸ {lens['lens']}" + ("" if lens.get("applicable", True) else f"  [不適用] {lens.get('note','')}"))
        if lens.get("data"):
            L.append("   資料:" + json.dumps(lens["data"], ensure_ascii=False))
        for f in lens.get("flags", []):
            L.append(f"   🚩 {f}")
        if lens.get("applicable", True) and not lens.get("flags"):
            L.append("   ✓ 無紅旗")
        if lens.get("caveat"):
            L.append(f"   ⚠ {lens['caveat']}")
    L.append("\n【散戶陷阱 / 心理層 — 對照你本人老毛病】")
    for f in o["psychology"]["flags"]:
        L.append(f"   🧠 {f}")
    L.append("\n【B 艙 判讀鏡頭 — 只列該問的攻擊問題,裁決需你主觀判讀、不自動下】")
    for b in o["B_judgment_lenses"]:
        L.append(f"\n▸ {b['lens']}")
        L.append(f"   問:{b['ask']}")
        L.append(f"   限:{b['limit']}")
    L.append("\n" + "=" * 70)
    L.append("📎 鏡頭層只攻擊訊號、輸出紅旗,不生成方向。方向由你的訊號+盤感決定。")
    L.append("   A艙紅旗可信(資料算出);B艙裁決是主觀判讀不進程式化欄位;心理層防你自己犯錯。")
    L.append("=" * 70)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default="SI=F")
    ap.add_argument("--claim-dir", default="up", choices=["up", "down"])
    ap.add_argument("--holding-dir", default=None, choices=["short", "long", None])
    ap.add_argument("--note", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    o = run(a.asset, a.claim_dir, a.holding_dir, a.note)
    if a.json:
        print(json.dumps(o, ensure_ascii=False, indent=2))
    else:
        print(render(o))


if __name__ == "__main__":
    main()
