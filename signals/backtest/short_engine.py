#!/usr/bin/env python3
"""COT 投機空頭(noncomm short)分位/趨勢 -> 白銀後續走勢 回測引擎

方法鐵則(與 engine.py 一致的精神,但改為週頻 COT 事件):
1. 前視偏誤防護:COT 報告日=週二,官方公布=當週五 15:30 ET(晚於 COMEX 白銀
   結算 13:30 ET)。故最早可交易收盤 = 報告日之後的下一個週一。
   實作:entry = 第一個交易日 >= report_date + LAG 天(預設 LAG=6 -> 週一)。
   另有 LAG=12(允許公布延遲,如 2018-19 政府關門)的穩健性變體。
2. rolling 分位只用「當週及過去」資料(strict pct,與 silver_daily.py fetch_cot 一致)。
3. 事件去重:冷卻 = H 個交易日(同一波只算一次)。
4. 排除未收盤 bar。
5. base rate = 同一組候選進場日(全部 COT 對齊日)的同 H 同方向命中率。
"""
import numpy as np
import pandas as pd
from scipy import stats as sps

COT_CSV = "/Volumes/workplace/EnglishTraining/market-radar/signals/backtest/cot_short_hist.csv"
PX_PKL = "/tmp/bt_si_raw.pkl"
LAST_CLOSED = pd.Timestamp("2026-08-06")   # 排除今日盤中未收盤 bar


def load_px():
    import pickle
    d = pickle.load(open(PX_PKL, "rb"))
    c = d["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    c = c.dropna()
    return c[c.index <= LAST_CLOSED]


def pct_strict(x):
    """最新值大於窗內其他值的比例(%)。只含當週及過去 -> 無前視。"""
    return (x.iloc[-1] > x.iloc[:-1]).mean() * 100 if len(x) > 1 else np.nan


def load_cot(lag_days=6):
    df = pd.read_csv(COT_CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    s = df.noncomm_short
    df["pct52"] = [pct_strict(s.iloc[max(0, i - 51):i + 1]) if i >= 25 else np.nan
                   for i in range(len(df))]
    df["pct26"] = [pct_strict(s.iloc[max(0, i - 25):i + 1]) if i >= 12 else np.nan
                   for i in range(len(df))]
    df["net4"] = s - s.shift(4)
    df["net8"] = s - s.shift(8)
    df["net2"] = s - s.shift(2)
    df["pct52_prev"] = df.pct52.shift(1)
    df["pct52_max8"] = df.pct52.rolling(8).max()
    df["short_pct_oi"] = s / df.open_interest_all * 100
    df["avail"] = df.date + pd.Timedelta(days=lag_days)
    return df


def attach_entry(cot, px):
    """把每個 COT 報告週對齊到可交易的進場日(index into px)。"""
    idx = px.index
    pos = idx.searchsorted(cot.avail.values, side="left")   # 第一個交易日 >= avail
    cot = cot.copy()
    cot["ipos"] = pos
    cot = cot[cot.ipos < len(idx)].copy()
    cot["entry_date"] = idx[cot.ipos.values]
    # 一週最多一個進場日;若因缺價造成重複,保留較新報告
    cot = cot.drop_duplicates(subset="ipos", keep="last").reset_index(drop=True)
    return cot


def fwd_ret(px, ipos, H):
    """進場日收盤 -> H 個交易日後收盤。"""
    n = len(px)
    v = px.values
    out = np.full(len(ipos), np.nan)
    ok = (ipos + H) < n
    out[ok] = v[ipos[ok] + H] / v[ipos[ok]] - 1
    return out


def dedup(mask, ipos, H):
    """事件去重:冷卻 H 個交易日。"""
    keep = np.zeros(len(mask), bool)
    last = -10 ** 9
    for i in np.where(mask)[0]:
        if ipos[i] - last >= H:
            keep[i] = True
            last = ipos[i]
    return keep


def bt(name, cot, px, cond, H, direction, cond_desc=""):
    ipos = cot.ipos.values
    fwd = fwd_ret(px, ipos, H)
    valid = ~np.isnan(fwd) & cot.pct52.notna().values
    m = cond.values if isinstance(cond, pd.Series) else cond
    m = m & valid
    keep = dedup(m, ipos, H)
    r = fwd[keep] * direction
    n = int(keep.sum())
    base_mask = valid
    br = fwd[base_mask] * direction
    base = (br > 0).mean() * 100
    bavg = br.mean() * 100
    if n == 0:
        return dict(name=name, H=H, dir=direction, n=0, wr=np.nan, base=round(base, 1),
                    edge=np.nan, avg=np.nan, bavg=round(bavg, 2), desc=cond_desc)
    hit = r > 0
    wr = hit.mean() * 100
    loss = r[~hit]
    p_binom = sps.binomtest(int(hit.sum()), n, base / 100, alternative="two-sided").pvalue
    # 報酬 t 檢定:事件報酬 vs 同窗 base 報酬(Welch)
    p_t = sps.ttest_ind(r, br, equal_var=False).pvalue
    # 半樣本分割
    ev = np.where(keep)[0]
    half = len(ev) // 2
    e1, e2 = ev[:half], ev[half:]
    def sub(e):
        rr = fwd[e] * direction
        return (round((rr > 0).mean() * 100, 1), round(rr.mean() * 100, 2), len(e))
    h1, h2 = sub(e1), sub(e2)
    same = "同向" if (h1[1] > 0) == (h2[1] > 0) and h1[0] > base and h2[0] > base else "翻向"
    return dict(name=name, H=H, dir=direction, n=n, wr=round(wr, 1), base=round(base, 1),
                edge=round(wr - base, 1), avg=round(r.mean() * 100, 2),
                med=round(float(np.median(r)) * 100, 2), bavg=round(bavg, 2),
                loss_med=round(float(np.median(loss)) * 100, 2) if len(loss) else np.nan,
                loss_worst=round(float(loss.min()) * 100, 2) if len(loss) else np.nan,
                p_binom=round(p_binom, 4), p_ttest=round(p_t, 4),
                h1=h1, h2=h2, half=same, desc=cond_desc,
                first=str(cot.entry_date.iloc[ev[0]].date()),
                last=str(cot.entry_date.iloc[ev[-1]].date()))


def fmt(rows):
    cols = ["name", "H", "dir", "n", "wr", "base", "edge", "avg", "med",
            "loss_med", "loss_worst", "p_binom", "p_ttest", "half"]
    return pd.DataFrame(rows)[cols].to_string(index=False)
