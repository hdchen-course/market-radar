"""
data_layer.py — 事件分類器的價格資料層(進版控、不依賴 /tmp、參數化 as-of)

取代舊 backtest/engine.py 硬讀 /tmp/px.pkl + 硬編 LAST_CLOSED 的做法。
用 yfinance 下載日線收盤,存到 repo 內 data/*.parquet,供回測重跑。

誠實限制:
- 免費 yfinance 資料,日線;財報事件用 yfinance get_earnings_dates() 的 Reported EPS
  (當時首刷值,無修訂 look-ahead)。宏觀 actual 值不在此層處理(FRED 存修訂後值會污染
  surprise 正負號),宏觀只用「排定日期」定位事件窗、不做 surprise。
"""
import os, sys, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# 標的 + 基準。貴金屬基準=GC(金);晶片基準=SOX/SMH(半導體指數)
TICKERS = {
    "SI=F": "silver", "GC=F": "gold",
    "NVDA": "nvda", "MU": "mu", "TSM": "tsm", "AMD": "amd",
    "^SOX": "sox", "SMH": "smh", "^GSPC": "spx",
}


def download_prices(period="6y", force=False):
    """下載日線收盤到 data/prices.pkl。force=True 強制重抓。"""
    import yfinance as yf
    path = os.path.join(DATA, "prices.pkl")
    if os.path.exists(path) and not force:
        print(f"[data_layer] 已存在 {path}(用 force=True 重抓)")
        return pd.read_pickle(path)
    frames = {}
    for sym in TICKERS:
        try:
            df = yf.Ticker(sym).history(period=period, auto_adjust=True)
            if len(df):
                frames[sym] = df["Close"].tz_localize(None)
                print(f"[data_layer] {sym}: {len(df)} bars {df.index[0].date()}~{df.index[-1].date()}")
            else:
                print(f"[data_layer] {sym}: 空,跳過")
        except Exception as e:
            print(f"[data_layer] {sym} 失敗: {e}")
    px = pd.DataFrame(frames)
    px.to_pickle(path)
    print(f"[data_layer] 存 {path}  shape={px.shape}")
    return px


def load_prices(as_of=None):
    """讀價格,可用 as_of 截斷(防前視:回測時只用 as_of 及更早)。"""
    path = os.path.join(DATA, "prices.pkl")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} 不存在,先跑 download_prices()")
    px = pd.read_pickle(path)
    if as_of is not None:
        px = px[px.index <= pd.Timestamp(as_of)]
    return px


if __name__ == "__main__":
    force = "--force" in sys.argv
    px = download_prices(force=force)
    print(px.tail(3).to_string())
