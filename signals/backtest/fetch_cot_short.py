#!/usr/bin/env python3
"""抓 CFTC 白銀 COT 投機空頭(noncomm short)完整歷史 -> backtest/cot_short_hist.csv

資料集:6dca-aqww(Disaggregated/Legacy Futures Only),合約碼 084691(SILVER - COMMEX)
欄位:noncomm_positions_short_all / noncomm_positions_long_all / open_interest_all

同時算出「當前」顯示數據,定義刻意與 silver_daily.py 的 fetch_cot() 一致:
  pct52 = (x.iloc[-1] > x.iloc[:-1]).mean() * 100   # strict,分母含自己 -> 用 52 週窗
  net4  = x.iloc[-1] - x.iloc[-5]                    # 4 週變化
"""
import json
import os
import urllib.parse
import urllib.request

import pandas as pd

BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
CODE = "084691"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cot_short_hist.csv")

COLS = ("report_date_as_yyyy_mm_dd,open_interest_all,"
        "noncomm_positions_long_all,noncomm_positions_short_all")


def fetch_all():
    """分頁抓完整歷史(Socrata 單次上限 50000,白銀週資料遠小於此,一次抓完)。"""
    rows, offset = [], 0
    while True:
        q = {"$limit": "5000",
             "$offset": str(offset),
             "$order": "report_date_as_yyyy_mm_dd ASC",
             "$select": COLS,
             "$where": f"cftc_contract_market_code='{CODE}'"}
        url = BASE + "?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        batch = json.load(urllib.request.urlopen(req, timeout=90))
        rows += batch
        if len(batch) < 5000:
            break
        offset += 5000
    return rows


def build(rows):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df.report_date_as_yyyy_mm_dd.str[:10])
    for c in ["open_interest_all", "noncomm_positions_long_all",
              "noncomm_positions_short_all"]:
        df[c] = pd.to_numeric(df[c])
    df = df.rename(columns={"noncomm_positions_short_all": "noncomm_short",
                            "noncomm_positions_long_all": "noncomm_long"})
    df["net"] = df.noncomm_long - df.noncomm_short
    df = (df[["date", "noncomm_short", "noncomm_long", "open_interest_all", "net"]]
          .drop_duplicates(subset="date")
          .sort_values("date")
          .reset_index(drop=True))
    return df


def pct_strict(x):
    """與 fetch_cot() 一致的 strict 百分位:最新值大於窗內其他值的比例(%)。"""
    return (x.iloc[-1] > x.iloc[:-1]).mean() * 100 if len(x) > 1 else float("nan")


def stats(df):
    s = df.noncomm_short
    out = {
        "date": str(df.date.iloc[-1].date()),
        "short": int(s.iloc[-1]),
        "long": int(df.noncomm_long.iloc[-1]),
        "net": int(df.net.iloc[-1]),
        "oi": int(df.open_interest_all.iloc[-1]),
        "short_pct52": round(pct_strict(s.iloc[-52:]), 1),
        "short_pct26": round(pct_strict(s.iloc[-26:]), 1),
        "short_pct_all": round(pct_strict(s), 1),
        "short_net4": int(s.iloc[-1] - s.iloc[-5]),
        "short_net8": int(s.iloc[-1] - s.iloc[-9]),
        "net_pct52": round(pct_strict(df.net.iloc[-52:]), 1),
        "net_net4": int(df.net.iloc[-1] - df.net.iloc[-5]),
        "short_pct_oi": round(s.iloc[-1] / df.open_interest_all.iloc[-1] * 100, 1),
        "n_weeks": len(df),
        "first_date": str(df.date.iloc[0].date()),
    }
    return out


if __name__ == "__main__":
    df = build(fetch_all())
    df.to_csv(OUT, index=False, date_format="%Y-%m-%d")
    st = stats(df)
    print(f"CSV -> {OUT}  ({st['n_weeks']} 週, {st['first_date']} ~ {st['date']})")
    print(json.dumps(st, ensure_ascii=False, indent=2))
    print("\n--- 最新 12 週原始數據 ---")
    tail = df.tail(12).copy()
    tail["date"] = tail.date.dt.strftime("%Y-%m-%d")
    print(tail.to_string(index=False))
    print("\n--- 近 8 週空單軌跡 ---")
    for _, r in df.tail(9).iterrows():
        print(f"  {r.date.date()}  short={int(r.noncomm_short):>7,}  "
              f"long={int(r.noncomm_long):>7,}  net={int(r.net):>7,}")
