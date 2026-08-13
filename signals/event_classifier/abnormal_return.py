"""
abnormal_return.py — 市場模型異常報酬 + pre-event drift(CAR)

AR_{i,t} = r_{i,t} − (α_i + β_i · r_bench,t)
  β_i 由估計窗 [t_e−N−EST_GAP−EST_LEN, t_e−N−EST_GAP] 回歸(嚴格早於 drift 窗,留 gap 防重疊/前視)
Pre-event drift = CAR_i[−N,−1] = Σ AR over N days before event

防前視三道:
1. β 用「事件前的估計窗」,且與 drift 窗之間留 EST_GAP 天
2. CAR 只累加 t_e−1 及更早的 AR
3. 事件日、進出場都用日線收盤,不含未來資料
"""
import numpy as np
import pandas as pd

EST_LEN = 120   # 估計窗長度(交易日)
EST_GAP = 5     # 估計窗與 drift 窗之間的緩衝


def _returns(px_asset, px_bench):
    r = px_asset.pct_change()
    rb = px_bench.pct_change()
    df = pd.DataFrame({"r": r, "rb": rb}).dropna()
    return df


def car_pre_event(px_asset, px_bench, event_date, N):
    """回傳事件前 N 日的累積異常報酬 CAR[-N,-1],及估計窗 AR 日標準差 σ_pre。
       資料不足回 (nan, nan)。全程只用 event_date 之前的資料。"""
    df = _returns(px_asset, px_bench)
    idx = df.index
    ed = pd.Timestamp(event_date).normalize()
    # 事件日在序列中的位置(取 <= ed 的最後一根)
    pos_arr = np.where(idx <= ed)[0]
    if len(pos_arr) == 0:
        return np.nan, np.nan
    te = pos_arr[-1]
    # drift 窗 = [te-N, te-1];估計窗 = [te-N-EST_GAP-EST_LEN, te-N-EST_GAP]
    est_hi = te - N - EST_GAP
    est_lo = est_hi - EST_LEN
    if est_lo < 1:
        return np.nan, np.nan
    est = df.iloc[est_lo:est_hi]
    if len(est) < EST_LEN * 0.8:
        return np.nan, np.nan
    # 市場模型回歸 r = a + b*rb
    x = est["rb"].values
    y = est["r"].values
    b, a = np.polyfit(x, y, 1)
    ar_est = y - (a + b * x)
    sigma = float(np.std(ar_est, ddof=1))
    # drift 窗 AR
    dr = df.iloc[te - N:te]  # te-N .. te-1
    if len(dr) < N * 0.8:
        return np.nan, np.nan
    ar_dr = dr["r"].values - (a + b * dr["rb"].values)
    car = float(np.sum(ar_dr))
    return car, sigma


def post_event_car(px_asset, px_bench, event_date, M):
    """事件後 CAR[+1,+M](次日進場後 M 日),用於『賣事實/利多出盡』的描述性觀察。
       僅描述,不放行進場。"""
    df = _returns(px_asset, px_bench)
    idx = df.index
    ed = pd.Timestamp(event_date).normalize()
    pos_arr = np.where(idx <= ed)[0]
    if len(pos_arr) == 0:
        return np.nan
    te = pos_arr[-1]
    # 估計窗同上(用事件前)
    N0 = 20
    est_hi = te - N0 - EST_GAP
    est_lo = est_hi - EST_LEN
    if est_lo < 1 or te + 1 + M >= len(df):
        return np.nan
    est = df.iloc[est_lo:est_hi]
    b, a = np.polyfit(est["rb"].values, est["r"].values, 1)
    post = df.iloc[te + 1:te + 1 + M]
    ar_post = post["r"].values - (a + b * post["rb"].values)
    return float(np.sum(ar_post))
