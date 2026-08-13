"""
backtest_drift.py — pre-event drift 回測(階段1 MVP 的唯一可驗證硬核)

回答:「某標的在財報前 N 日,相對基準的異常報酬,歷史上系統性偏多/偏空/無方向?
       去重、分年 walk-forward 後還站得住嗎?」

嚴守 reviewer 訂的閘門(全部通過才標「可參考傾向」,否則「僅描述」):
  1. N_events >= 8         (樣本紅線,沿用白銀工具 hard_caps N<8→不可用)
  2. |edge| 有意義          (CAR 方向一致率 vs 50%)
  3. 顯著性 binom p<0.05
  4. walk-forward 逐年方向一致 > 50% 年數
  5. 禁止跨標的/跨事件類型池化(每檔分開報)
  6. 5/10/20 三窗強制全報,禁止事後挑最好看

輸出純描述統計 + 誠實 verdict,不給「買賣訊號」。
"""
import sys, os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from data_layer import load_prices
from events import build_earnings_calendar
from abnormal_return import car_pre_event, post_event_car

BENCH = {"NVDA": "^SOX", "MU": "^SOX", "TSM": "^SOX", "AMD": "^SOX"}
WINDOWS = [5, 10, 20]
POST_M = 5


def run_ticker(ticker, px, cal, N):
    """對單一標的、單一 drift 窗 N 回測。回傳描述統計 dict。"""
    if ticker not in px.columns:
        return None
    bench = BENCH.get(ticker, "^GSPC")
    a = px[ticker].dropna()
    b = px[bench].dropna()
    evs = cal[cal.ticker == ticker].sort_values("date")
    cars, posts, surprises, years = [], [], [], []
    last_used = None
    for _, e in evs.iterrows():
        ed = e["date"]
        # 只用有價格覆蓋的事件(估計窗+drift窗需落在資料內)
        if ed < a.index[0] + pd.Timedelta(days=260) or ed > a.index[-1]:
            continue
        # 去重:財報本就季度間隔,同一事件不重複(財報天然 >8 週間隔,無需額外冷卻)
        car, sigma = car_pre_event(a, b, ed, N)
        if np.isnan(car) or np.isnan(sigma) or sigma == 0:
            continue
        cars.append(car)
        posts.append(post_event_car(a, b, ed, POST_M))
        surprises.append(e.get("surprise_pct", np.nan))
        years.append(ed.year)
        last_used = ed
    n = len(cars)
    if n == 0:
        return dict(ticker=ticker, N=N, n=0, verdict="無樣本")
    cars = np.array(cars, float)
    up_rate = float((cars > 0).mean()) * 100     # 事件前偏多比率
    mean_car = float(np.mean(cars)) * 100          # 平均 CAR(%)
    med_car = float(np.median(cars)) * 100
    # 方向一致性檢定:CAR>0 的比率 vs 50%
    k = int((cars > 0).sum())
    p_binom = stats.binomtest(k, n, 0.5).pvalue if n > 0 else np.nan
    # walk-forward:逐年多數方向是否 > 50% 年數
    dfy = pd.DataFrame({"car": cars, "yr": years})
    yr_dir = dfy.groupby("yr")["car"].apply(lambda s: 1 if s.mean() > 0 else (-1 if s.mean() < 0 else 0))
    dominant = 1 if mean_car > 0 else -1
    yrs_agree = int((yr_dir == dominant).sum())
    yrs_total = int((yr_dir != 0).sum())
    wf_pass = (yrs_total > 0 and yrs_agree / yrs_total > 0.5)
    # 賣事實觀察(描述,不放行):大幅正drift 事件的 post-event CAR
    posts = np.array([p for p in posts if not (p is None or np.isnan(p))], float)
    post_mean = float(np.mean(posts)) * 100 if len(posts) else np.nan

    # verdict 閘門
    reasons = []
    if n < 8: reasons.append(f"N={n}<8")
    if p_binom is not None and p_binom >= 0.05: reasons.append(f"p={p_binom:.2f}≥0.05")
    if not wf_pass: reasons.append(f"walk-forward {yrs_agree}/{yrs_total}未過半")
    if abs(up_rate - 50) < 12: reasons.append(f"方向一致率{up_rate:.0f}%接近50%")
    verdict = "可參考傾向" if not reasons else "僅描述"

    return dict(ticker=ticker, N=N, n=n, up_rate=round(up_rate, 1),
                mean_car=round(mean_car, 3), med_car=round(med_car, 3),
                p_binom=round(float(p_binom), 4) if p_binom is not None else None,
                wf=f"{yrs_agree}/{yrs_total}", post_mean=round(post_mean, 3) if not np.isnan(post_mean) else None,
                verdict=verdict, why=";".join(reasons) if reasons else "全閘通過")


def main():
    px = load_prices()
    cal = build_earnings_calendar()
    print("=" * 78)
    print("pre-event drift 回測 — 財報前 CAR(相對 ^SOX 基準),晶片股")
    print("價格覆蓋:", px.index[0].date(), "~", px.index[-1].date())
    print("=" * 78)
    print(f"{'標的':<6}{'N窗':<5}{'事件數':<6}{'偏多%':<7}{'均CAR%':<9}{'中CAR%':<9}{'binom_p':<9}{'逐年WF':<8}{'事後CAR%':<9}{'判定':<12}")
    print("-" * 78)
    rows = []
    for tk in ["NVDA", "MU", "TSM", "AMD"]:
        for N in WINDOWS:   # 強制三窗全報
            r = run_ticker(tk, px, cal, N)
            if r is None or r.get("n", 0) == 0:
                print(f"{tk:<6}{N:<5}{'—':<6}無樣本")
                continue
            rows.append(r)
            print(f"{r['ticker']:<6}{r['N']:<5}{r['n']:<6}{r['up_rate']:<7}{r['mean_car']:<9}{r['med_car']:<9}"
                  f"{str(r['p_binom']):<9}{r['wf']:<8}{str(r['post_mean']):<9}{r['verdict']:<12} {r['why']}")
    print("-" * 78)
    passed = [r for r in rows if r["verdict"] == "可參考傾向"]
    print(f"\n通過全閘門(可參考傾向)的組合:{len(passed)} / {len(rows)}")
    if not passed:
        print("→ 誠實結論:目前無任何組合通過樣本+顯著+walk-forward 三閘,全部僅供描述。")
        print("   (這是正確結果不是失敗——晶片股財報前 drift 在 6 年約24事件的樣本上,")
        print("    數學上很難撐起可交易的統計顯著性,如白銀工具所示。)")
    else:
        for r in passed:
            print(f"   ✅ {r['ticker']} N={r['N']}: 事件前偏{'多' if r['mean_car']>0 else '空'} "
                  f"均CAR {r['mean_car']}% (n={r['n']}, p={r['p_binom']}, WF {r['wf']})")
    return rows


if __name__ == "__main__":
    main()
