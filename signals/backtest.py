#!/usr/bin/env python3
"""radar.scenario_engine 判讀層的 walk-forward 回測與門檻校準。

目的：radar.py 的 _DIM_WEIGHT（維度權重）與 _VERDICT_HI/_LO（信心門檻）原本是
「經驗值、未經回測」。本工具用歷史 K 線做 point-in-time 重建，驗證：
  (1) 加權 verdict 方向（偏多→漲 / 偏空→跌）命中率有沒有打敗 baseline；
  (2) 高信心桶是不是真的比低信心桶準；
  (3) 加權計分 vs 等權計分 有沒有差；
  (4) 小網格搜尋門檻與前瞻窗 h，並用 train/test 時間切分看 out-of-sample 是否仍成立。

★誠實鐵則（比照白銀工具前例：回測後 0 clean signals 就要明寫）：若 out-of-sample
沒有統計顯著 edge，就明寫「無 edge、門檻維持原值」，不准粉飾。

★範圍聲明：funding 與 macro 設為中性（歷史 point-in-time 難對齊），故本回測只驗證
「技術核心」＝ CVD結構 + CVD短線 + SuperTrend + VolumeProfile + K線形態，**不含**
funding/宏觀兩個維度。那兩維的權重本回測無法背書。

★多尺度與多框 ST 的 point-in-time 近似（必須誠實標明，非 radar 線上版的原樣）：
  - 多尺度 CVD：線上版抓 1d/4h/1h/15m 不同 interval；回測只用單一 base interval，
    以「長窗 vs 短窗」近似 結構 vs 當下（結構=長 lookback、當下=短 lookback）。
  - 多框 SuperTrend：線上版 1d/4h/1h 三 interval；回測在同一 base interval 上用
    三個不同 ATR 週期（短/中/長）近似三框的共識/背離。
  這些近似足以驗證「verdict 分數的方向性有無預測力」，但不是線上版的逐欄複刻。

純標準庫。用法：python3 backtest.py（或 .venv/bin/python backtest.py）。
"""
import json
import sys
import urllib.request

sys.path.insert(0, ".")
import cvd_multi as cvd  # noqa: E402
import radar  # noqa: E402

_UA = {"User-Agent": "Mozilla/5.0"}
_TIMEOUT = 30
_BASE = "https://fapi.binance.com/fapi/v1"

# 回測設定
_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
_INTERVAL = "4h"            # 4h：6 根≈1 天、24 根≈4 天
_TOTAL_BARS = 3000          # 每標的目標根數（分頁抓）
_STRUCT_WIN = 60            # 「結構」長窗（根）
_SHORT_WIN = 12             # 「當下」短窗（根）
_VP_WIN = 180               # Volume Profile 取樣窗（根）
_ST_PERIODS = [60, 120, 240]  # 三框 SuperTrend 的 ATR 週期近似（短/中/長）
_MIN_T = 260                # 需要足夠歷史才開始評估（最長 ST 週期 + 緩衝）
_HORIZONS = [6, 12, 24]     # 前瞻窗（根）
# 門檻網格（校準對象）
_GRID_HI = [2.0, 3.0, 4.0, 5.0, 6.0]
_GRID_LO = [1.0, 1.5, 2.0, 2.5, 3.0]
_MIN_CALLS = 30             # 一個門檻組合至少要這麼多次方向呼叫才採信


def _get_json(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.load(resp)


def fetch_klines(symbol, interval, total):
    """分頁往回抓 klines，回傳時間升冪的 [(open,high,low,close,vol,taker_buy), ...]。"""
    out = []
    end_time = None
    while len(out) < total:
        url = f"{_BASE}/klines?symbol={symbol}&interval={interval}&limit=1500"
        if end_time is not None:
            url += f"&endTime={end_time}"
        batch = _get_json(url)
        if not batch:
            break
        rows = [(float(k[1]), float(k[2]), float(k[3]), float(k[4]),
                 float(k[5]), float(k[9])) for k in batch]
        # batch 為升冪；接到既有資料前面
        out = rows + out if end_time is not None else rows
        end_time = int(batch[0][0]) - 1  # 下一頁抓更舊的
        if len(batch) < 1500:
            break
    # 去重＋升冪（分頁接合保險）
    return out[-total:] if len(out) > total else out


def cvd_rows(bars):
    """把 (o,h,l,c,vol,taker) 轉成 cvd.summarize_scale 吃的 (close, delta, vol)。"""
    return [(b[3], 2 * b[5] - b[4], b[4]) for b in bars]


def vp_from_bars(bars):
    """複刻 radar.volume_profile 的分桶（50 桶、0.70 Value Area），餵歷史窗格。"""
    prices_vols = [(b[3], b[4]) for b in bars]
    lo = min(p for p, _ in prices_vols)
    hi = max(p for p, _ in prices_vols)
    width = (hi - lo) / 50 or 1.0
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
        if acc >= total * 0.70:
            break
    return {"poc": poc, "vah": lo + (max(chosen) + 1) * width, "val": lo + min(chosen) * width}


def st_dir_from_bars(bars, period):
    """複刻 radar.supertrend_dir（ATR=RMA(TR,period)、mid±3ATR）餵歷史窗格。"""
    highs = [b[1] for b in bars]
    lows = [b[2] for b in bars]
    closes = [b[3] for b in bars]
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    atr = radar._rma(trs, period)[-1] if len(trs) > period else sum(trs) / len(trs)
    mid = (highs[-1] + lows[-1]) / 2
    upper, lower, close = mid + 3 * atr, mid - 3 * atr, closes[-1]
    return "多" if close > upper else ("空" if close < lower else "中")


_NEUTRAL_FUNDING = {"funding_pct": None, "pctile": None}
_NEUTRAL_MACRO = {"10Y": None, "DXY": None, "VIX": None, "HY_OAS": None, "HY_OAS_up": None}


def build_point(bars_upto):
    """用到時點 t（含）的歷史重建 scenario_engine 的輸入並跑，回傳
    (bull_w, bear_w, bull_e, bear_e)：加權與等權的多空分數。"""
    rows = cvd_rows(bars_upto)
    struct = cvd.summarize_scale(rows[-_STRUCT_WIN:])
    short = cvd.summarize_scale(rows[-_SHORT_WIN:])
    cvd_results = {"結構 1d": struct, "當下 15m": short}
    vp = vp_from_bars(bars_upto[-_VP_WIN:])
    st = {f"f{i}": {"dir": st_dir_from_bars(bars_upto, p)}
          for i, p in enumerate(_ST_PERIODS)}
    candles = radar.detect_candles([(b[0], b[1], b[2], b[3]) for b in bars_upto[-3:]])
    sc = radar.scenario_engine({"price": bars_upto[-1][3]}, cvd_results, vp, st,
                               _NEUTRAL_FUNDING, _NEUTRAL_MACRO, candles)
    # 等權：同一批訊號改用權重 1（訊號 tuple = (dim,dir,strength,weight,reason)）
    bull_e = sum(s[2] for s in sc["bull"])
    bear_e = sum(s[2] for s in sc["bear"])
    return sc["bull_score"], sc["bear_score"], bull_e, bear_e


def run_symbol(symbol):
    """回傳 per-t 記錄 list：{i, diff_w, diff_e} 及該標的 closes。"""
    bars = fetch_klines(symbol, _INTERVAL, _TOTAL_BARS)
    closes = [b[3] for b in bars]
    records = []
    last = len(bars) - 1 - max(_HORIZONS)   # 要留得出前瞻報酬
    for t in range(_MIN_T, last + 1):
        bw, br, ew, er = build_point(bars[:t + 1])
        records.append({"i": t, "diff_w": bw - br, "diff_e": ew - er})
    return records, closes


def fwd_ret(closes, i, h):
    j = i + h
    return closes[j] / closes[i] - 1 if j < len(closes) else None


def classify(diff, lo):
    if diff >= lo:
        return 1       # 偏多
    if diff <= -lo:
        return -1      # 偏空
    return 0           # 區間/分歧


def eval_combo(recs, closes, lo, hi, h):
    """回傳 (n_calls, hit_rate, n_hi, hit_hi, mean_long, mean_short, baseline_up)。"""
    ups = 0
    fwds_all = []
    calls = []  # (sign, fwd, is_hi)
    for r in recs:
        f = fwd_ret(closes, r["i"], h)
        if f is None:
            continue
        fwds_all.append(f)
        if f > 0:
            ups += 1
        sign = classify(r["diff_w"], lo)
        if sign != 0:
            calls.append((sign, f, abs(r["diff_w"]) >= hi))
    baseline_up = ups / len(fwds_all) if fwds_all else 0.0
    if not calls:
        return 0, 0.0, 0, 0.0, 0.0, 0.0, baseline_up
    hits = sum(1 for s, f, _ in calls if (s == 1 and f > 0) or (s == -1 and f < 0))
    hi_calls = [(s, f) for s, f, ih in calls if ih]
    hit_hi = (sum(1 for s, f in hi_calls if (s == 1 and f > 0) or (s == -1 and f < 0))
              / len(hi_calls)) if hi_calls else 0.0
    longs = [f for s, f, _ in calls if s == 1]
    shorts = [f for s, f, _ in calls if s == -1]
    mean_long = sum(longs) / len(longs) if longs else 0.0
    mean_short = sum(shorts) / len(shorts) if shorts else 0.0
    return (len(calls), hits / len(calls), len(hi_calls), hit_hi,
            mean_long, mean_short, baseline_up)


def eval_equal(recs, closes, lo, h):
    """等權版方向命中率（與加權對照）。"""
    calls = []
    for r in recs:
        f = fwd_ret(closes, r["i"], h)
        if f is None:
            continue
        sign = classify(r["diff_e"], lo)
        if sign != 0:
            calls.append((sign, f))
    if not calls:
        return 0, 0.0
    hits = sum(1 for s, f in calls if (s == 1 and f > 0) or (s == -1 and f < 0))
    return len(calls), hits / len(calls)


def main():
    print("=" * 72)
    print("radar.scenario_engine walk-forward 回測（技術核心；不含 funding/宏觀）")
    print(f"標的={_SYMBOLS}  interval={_INTERVAL}  目標根數={_TOTAL_BARS}")
    print("近似：多尺度CVD=長窗vs短窗、多框ST=三ATR週期；funding/macro 設中性")
    print("=" * 72)

    all_recs, all_closes = {}, {}
    for sym in _SYMBOLS:
        try:
            recs, closes = run_symbol(sym)
            all_recs[sym] = recs
            all_closes[sym] = closes
            print(f"[{sym}] 取得 {len(closes)} 根、評估點 {len(recs)} 個")
        except Exception as exc:
            print(f"[{sym}] 取得/評估失敗：{exc}")

    if not all_recs:
        print("\n⚠ 無資料，回測中止。門檻維持原值。")
        return 1

    # 合併所有標的（但 i 對應各自 closes，故 eval 需逐標的做再加總）
    def pooled_eval(lo, hi, h, idxset):
        tot_calls = tot_hits = tot_hi = tot_hi_hits = 0
        longs, shorts, ups, n_all = [], [], 0, 0
        for sym, recs in all_recs.items():
            closes = all_closes[sym]
            sub = [r for k, r in enumerate(recs) if k in idxset[sym]] if idxset else recs
            for r in sub:
                f = fwd_ret(closes, r["i"], h)
                if f is None:
                    continue
                n_all += 1
                if f > 0:
                    ups += 1
                sign = classify(r["diff_w"], lo)
                if sign == 0:
                    continue
                tot_calls += 1
                hit = (sign == 1 and f > 0) or (sign == -1 and f < 0)
                tot_hits += hit
                if sign == 1:
                    longs.append(f)
                else:
                    shorts.append(f)
                if abs(r["diff_w"]) >= hi:
                    tot_hi += 1
                    tot_hi_hits += hit
        baseline = ups / n_all if n_all else 0.0
        return {
            "calls": tot_calls,
            "hit": tot_hits / tot_calls if tot_calls else 0.0,
            "hi_calls": tot_hi,
            "hit_hi": tot_hi_hits / tot_hi if tot_hi else 0.0,
            "mean_long": sum(longs) / len(longs) if longs else 0.0,
            "mean_short": sum(shorts) / len(shorts) if shorts else 0.0,
            "baseline": baseline,
            "n_all": n_all,
        }

    # train/test 時間切分（各標的前 70% 調、後 30% 驗）
    train_idx, test_idx = {}, {}
    for sym, recs in all_recs.items():
        cut = int(len(recs) * 0.70)
        train_idx[sym] = set(range(cut))
        test_idx[sym] = set(range(cut, len(recs)))

    # --- 原始門檻（HI=4,LO=2）在全樣本的表現（當基準快照）---
    print("\n--- 原始門檻 HI=4.0 LO=2.0 全樣本表現 ---")
    for h in _HORIZONS:
        r = pooled_eval(2.0, 4.0, h, None)
        print(f"h={h:>2}根 | 方向呼叫 {r['calls']:>4} 命中率 {r['hit']:.3f} "
              f"(baseline多頭佔比 {r['baseline']:.3f}) | 高信心 {r['hi_calls']:>3} "
              f"命中 {r['hit_hi']:.3f} | 偏多均報酬 {r['mean_long']:+.4f} "
              f"偏空均報酬 {r['mean_short']:+.4f}")

    # --- 加權 vs 等權（原門檻、各 h）---
    print("\n--- 加權 vs 等權 方向命中率（LO=2.0，全樣本）---")
    for h in _HORIZONS:
        w = pooled_eval(2.0, 4.0, h, None)
        # 等權逐標的
        ec = eh = 0
        for sym, recs in all_recs.items():
            n, hit = eval_equal(recs, all_closes[sym], 2.0, h)
            ec += n
            eh += int(hit * n)
        e_hit = eh / ec if ec else 0.0
        print(f"h={h:>2}根 | 加權命中 {w['hit']:.3f}({w['calls']}次) | "
              f"等權命中 {e_hit:.3f}({ec}次)")

    # --- 網格搜尋：train 選最佳，test 驗證 ---
    print("\n--- 門檻網格搜尋（train=前70%）目標：命中率 × 樣本足夠 ---")
    best = None
    for h in _HORIZONS:
        for lo in _GRID_LO:
            for hi in _GRID_HI:
                if hi < lo:
                    continue
                tr = pooled_eval(lo, hi, h, train_idx)
                if tr["calls"] < _MIN_CALLS:
                    continue
                # edge：方向命中率超出 0.5 的幅度（多空對稱指標）
                edge = tr["hit"] - 0.5
                if best is None or edge > best[0]:
                    best = (edge, h, lo, hi, tr)
    if best is None:
        print("⚠ train 無任何門檻組合達最低呼叫數，樣本不足。門檻維持原值。")
        return 0
    _, bh, blo, bhi, btr = best
    te = pooled_eval(blo, bhi, bh, test_idx)
    print(f"train 最佳：h={bh} LO={blo} HI={bhi} → 命中 {btr['hit']:.3f} "
          f"({btr['calls']}次, baseline {btr['baseline']:.3f})")
    print(f"test 驗證 ：h={bh} LO={blo} HI={bhi} → 命中 {te['hit']:.3f} "
          f"({te['calls']}次, baseline {te['baseline']:.3f}) | "
          f"偏多均報酬 {te['mean_long']:+.4f} 偏空均報酬 {te['mean_short']:+.4f}")
    print(f"test 高信心(|diff|>={bhi})：{te['hi_calls']}次 命中 {te['hit_hi']:.3f}")

    # --- 裁決 ---
    print("\n" + "=" * 72)
    print("裁決（誠實）")
    print("=" * 72)
    edge_vs_base = te["hit"] - max(te["baseline"], 1 - te["baseline"])
    long_edge = te["mean_long"] - 0.0
    short_edge = -te["mean_short"]
    if te["calls"] < _MIN_CALLS:
        print("test 樣本不足以斷言 → 無統計顯著 edge，門檻維持原值。")
    elif edge_vs_base <= 0.0:
        print(f"test out-of-sample 命中率 {te['hit']:.3f} 未打敗 baseline "
              f"{max(te['baseline'], 1 - te['baseline']):.3f}")
        print("→ 無統計顯著方向 edge。門檻維持原值，radar 定位維持『客觀儀表板』非買賣訊號。")
    else:
        print(f"test out-of-sample 命中率 {te['hit']:.3f} 超出 baseline "
              f"{edge_vs_base:+.3f}；偏多均報酬 {long_edge:+.4f} 偏空均報酬方向 {short_edge:+.4f}")
        hi_better = te["hit_hi"] > te["hit"]
        print(f"→ 有微弱 edge。高信心桶{'確實更準' if hi_better else '並未更準（信心分級存疑）'}。")
        print(f"→ 建議：h={bh} LO={blo} HI={bhi}（但樣本有限、單一資產類別、"
              "且不含 funding/宏觀，請視為軟性校準非保證）。")
    print("\n★範圍再聲明：本回測只驗證技術核心五維，funding 與宏觀維度未被背書；")
    print("  近似重建非 radar 線上版逐欄複刻；結論僅供門檻參考，不改變『需人工補情境』定位。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
