"""
events.py — 事件日曆抓取

財報事件:yfinance get_earnings_dates() → 財報日 + Reported EPS(當時首刷值,無修訂 look-ahead)。
         這是 MVP 的主力事件類型(reviewer 判定唯一無前視污染的 surprise 來源)。

宏觀事件:只用「排定日期」定位 event window,不抓 actual/surprise(FRED 存修訂後值會
         污染 surprise 正負號,reviewer 攻擊#3)。MVP 宏觀事件日期先用手動維護的清單
         (CPI/NFP/FOMC 每月一次,可從公開日曆補),只貢獻 pre-event drift 樣本、不做 surprise。
"""
import os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

CHIP_TICKERS = ["NVDA", "MU", "TSM", "AMD"]


def fetch_earnings(ticker, limit=40):
    """回傳 DataFrame[date, eps_est, eps_actual, surprise_pct]。
       eps_actual 是 yfinance 的 Reported EPS = 當時公布值(無修訂污染)。"""
    import yfinance as yf
    t = yf.Ticker(ticker)
    try:
        df = t.get_earnings_dates(limit=limit)
    except Exception as e:
        print(f"[events] {ticker} 財報抓取失敗: {e}")
        return pd.DataFrame()
    if df is None or not len(df):
        return pd.DataFrame()
    df = df.reset_index()
    # 欄位名跨版本有差異,容錯抓取
    col = {c.lower().strip(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in col:
                return col[n]
        return None
    c_date = pick("earnings date", "earnings date ")
    c_est = pick("eps estimate")
    c_act = pick("reported eps")
    c_sup = pick("surprise(%)", "surprise (%)", "surprise%")
    if c_date is None:
        return pd.DataFrame()
    out = pd.DataFrame({
        "date": pd.to_datetime(df[c_date]).dt.tz_localize(None).dt.normalize(),
        "eps_est": df[c_est] if c_est else pd.NA,
        "eps_actual": df[c_act] if c_act else pd.NA,
        "surprise_pct": df[c_sup] if c_sup else pd.NA,
    })
    # 只留已公布(actual 非空)的過去事件
    out = out[out["eps_actual"].notna()].sort_values("date").reset_index(drop=True)
    out["ticker"] = ticker
    return out


def build_earnings_calendar(force=False):
    path = os.path.join(DATA, "earnings.pkl")
    if os.path.exists(path) and not force:
        print(f"[events] 已存在 {path}")
        return pd.read_pickle(path)
    frames = []
    for tk in CHIP_TICKERS:
        e = fetch_earnings(tk)
        if len(e):
            frames.append(e)
            print(f"[events] {tk}: {len(e)} 筆財報 {e.date.min().date()}~{e.date.max().date()}")
    cal = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    cal.to_pickle(path)
    print(f"[events] 存 {path}  {len(cal)} 筆")
    return cal


if __name__ == "__main__":
    cal = build_earnings_calendar(force="--force" in sys.argv)
    if len(cal):
        # 每檔事件數(去重前)
        print(cal.groupby("ticker").size().to_string())
        print(cal.tail(5).to_string())
