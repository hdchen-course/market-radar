"""
Market Data Collector
=====================
Fetches data from multiple sources and saves as JSON/CSV for dashboard rendering.

Data sources:
  - FRED (Federal Reserve Economic Data): macro, yields, liquidity, CPI, etc.
  - Yahoo Finance: equities, commodities, ETFs, indices
  - CFTC COT: Commitments of Traders positioning data
  - AAII: Investor sentiment survey

Usage:
  python collect.py              # fetch all data
  python collect.py --source fred   # fetch only FRED data
  python collect.py --source yf     # fetch only Yahoo Finance data

Output:
  data/fred_data.json
  data/yfinance_data.json
  data/cot_data.json
  data/aaii_data.json
  data/metadata.json   (timestamps, comparison calculations)
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from config import (
    FRED_API_KEY, FRED_SERIES, YFINANCE_TICKERS,
    COT_CONTRACTS, AAII_URL, COMPARISON_PERIODS,
    DATA_DIR
)

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def ensure_dirs():
    """Create output directories if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# FRED Data Collection
# ============================================================

def collect_fred():
    """
    Fetch all configured FRED series.
    Returns dict: { series_id: { name, category, values: [{date, value}], comparisons: {...} } }
    """
    if not FRED_API_KEY:
        print("ERROR: FRED_API_KEY not set. Skipping FRED data.")
        print("  Get a free key: https://fred.stlouisfed.org/docs/api/api_key.html")
        print("  Then: export FRED_API_KEY=your_key_here")
        return {}

    from fredapi import Fred
    fred = Fred(api_key=FRED_API_KEY)

    results = {}
    # Flatten all categories into one list
    all_series = []
    for category_group, series_list in FRED_SERIES.items():
        for series_id, name, category in series_list:
            all_series.append((series_id, name, category, category_group))

    print(f"Fetching {len(all_series)} FRED series...")

    for series_id, name, category, group in all_series:
        try:
            # Fetch last 2 years of data for comparison purposes
            start_date = datetime.now() - timedelta(days=730)
            data = fred.get_series(series_id, observation_start=start_date)

            if data is None or data.empty:
                print(f"  WARN: No data for {series_id} ({name})")
                continue

            # Convert to list of {date, value} dicts
            values = [
                {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 4)}
                for d, v in data.dropna().items()
            ]

            # Calculate period-over-period comparisons
            comparisons = _calculate_comparisons(data.dropna())

            results[series_id] = {
                "name": name,
                "category": category,
                "group": group,
                "latest": values[-1] if values else None,
                "comparisons": comparisons,
                "values_count": len(values),
                # Store only last 60 data points to keep file size reasonable
                "recent_values": values[-60:],
            }
            print(f"  OK: {series_id} ({name}) - {len(values)} points")

        except Exception as e:
            print(f"  ERROR: {series_id} ({name}): {e}")

    return results


# ============================================================
# Yahoo Finance Data Collection
# ============================================================

def collect_yfinance():
    """
    Fetch price data for all configured tickers.
    Returns dict: { ticker: { name, category, price, change_pct, comparisons, ... } }
    """
    results = {}

    # Flatten all ticker groups
    all_tickers = []
    for group_name, ticker_list in YFINANCE_TICKERS.items():
        for ticker, name, category in ticker_list:
            all_tickers.append((ticker, name, category, group_name))

    print(f"Fetching {len(all_tickers)} Yahoo Finance tickers...")

    # Batch download for efficiency (1 year of daily data)
    ticker_symbols = [t[0] for t in all_tickers]
    try:
        raw_data = yf.download(
            ticker_symbols,
            period="1y",
            interval="1d",
            progress=False,
            group_by="ticker"
        )
    except Exception as e:
        print(f"  ERROR: Batch download failed: {e}")
        return {}

    for ticker, name, category, group in all_tickers:
        try:
            # Extract this ticker's close prices
            if len(ticker_symbols) == 1:
                closes = raw_data["Close"].dropna()
            else:
                closes = raw_data[ticker]["Close"].dropna()

            if closes.empty:
                print(f"  WARN: No data for {ticker} ({name})")
                continue

            latest_price = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2]) if len(closes) > 1 else latest_price

            # Period comparisons
            comparisons = _calculate_comparisons(closes)

            results[ticker] = {
                "name": name,
                "category": category,
                "group": group,
                "latest_price": round(latest_price, 2),
                "prev_close": round(prev_close, 2),
                "daily_change_pct": round((latest_price - prev_close) / prev_close * 100, 2),
                "comparisons": comparisons,
            }
            print(f"  OK: {ticker} ({name}) ${latest_price:.2f}")

        except Exception as e:
            print(f"  ERROR: {ticker} ({name}): {e}")

    return results


# ============================================================
# CFTC COT Data Collection
# ============================================================

def collect_cot():
    """
    Fetch latest CFTC Commitments of Traders data.
    Uses the CFTC bulk CSV download (futures-only, short format).

    Returns dict of positioning data per contract.
    """
    print("Fetching CFTC COT data...")

    # CFTC annual zip with proper headers (futures-only, legacy format)
    import zipfile
    year = datetime.now().year
    cot_url = f"https://www.cftc.gov/files/dea/history/deacot{year}.zip"

    try:
        resp = requests.get(cot_url, headers=HTTP_HEADERS, timeout=60)
        resp.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, low_memory=False)
        df.columns = [c.strip() for c in df.columns]

        results = {}
        for contract_code, name, category in COT_CONTRACTS:
            contract_data = df[df["CFTC Contract Market Code"].astype(str).str.strip() == contract_code]

            if contract_data.empty:
                print(f"  WARN: No COT data for {contract_code} ({name})")
                continue

            latest = contract_data.sort_values("As of Date in Form YYMMDD", ascending=False).iloc[0]

            noncomm_long = int(latest.get("Noncommercial Positions-Long (All)", 0))
            noncomm_short = int(latest.get("Noncommercial Positions-Short (All)", 0))
            comm_long = int(latest.get("Commercial Positions-Long (All)", 0))
            comm_short = int(latest.get("Commercial Positions-Short (All)", 0))
            open_interest = int(latest.get("Open Interest (All)", 0))

            net_speculative = noncomm_long - noncomm_short
            net_commercial = comm_long - comm_short

            results[contract_code] = {
                "name": name,
                "category": category,
                "report_date": str(latest.get("As of Date in Form YYYY-MM-DD", "")),
                "net_speculative": net_speculative,
                "net_commercial": net_commercial,
                "noncomm_long": noncomm_long,
                "noncomm_short": noncomm_short,
                "comm_long": comm_long,
                "comm_short": comm_short,
                "open_interest": open_interest,
                # Net spec as % of open interest (positioning intensity)
                "spec_pct_oi": round(net_speculative / open_interest * 100, 2) if open_interest > 0 else 0,
            }
            print(f"  OK: {name} - Net Spec: {net_speculative:+,}")

    except Exception as e:
        print(f"  ERROR: COT fetch failed: {e}")
        return {}

    return results


# ============================================================
# AAII Sentiment Survey
# ============================================================

def collect_aaii():
    """
    Fetch AAII Investor Sentiment Survey data.
    Returns latest bullish/bearish/neutral percentages + historical context.
    """
    print("Fetching AAII sentiment data...")

    try:
        resp = requests.get(AAII_URL, headers=HTTP_HEADERS, timeout=30)
        resp.raise_for_status()
        if resp.content[:5] == b'<html' or len(resp.content) < 10000:
            print("  WARN: AAII returned HTML instead of Excel (blocked). Using fallback.")
            return {"error": "AAII blocked direct download. Check manually at aaii.com/sentimentsurvey"}
        df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, engine='xlrd')

        # The spreadsheet has columns like: Date, Bullish, Neutral, Bearish, ...
        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Find the relevant columns (they vary slightly by year)
        date_col = [c for c in df.columns if "date" in c][0]
        bull_col = [c for c in df.columns if "bull" in c][0]
        bear_col = [c for c in df.columns if "bear" in c][0]
        neutral_col = [c for c in df.columns if "neutral" in c][0]

        df = df[[date_col, bull_col, bear_col, neutral_col]].dropna()
        df.columns = ["date", "bullish", "bearish", "neutral"]

        # Convert percentages (they might be 0-1 or 0-100)
        if df["bullish"].max() <= 1.0:
            df["bullish"] = df["bullish"] * 100
            df["bearish"] = df["bearish"] * 100
            df["neutral"] = df["neutral"] * 100

        latest = df.iloc[-1]
        prev_week = df.iloc[-2] if len(df) > 1 else latest

        # Historical averages (all-time)
        hist_avg_bull = round(df["bullish"].mean(), 1)
        hist_avg_bear = round(df["bearish"].mean(), 1)

        result = {
            "latest_date": str(latest["date"]),
            "bullish": round(float(latest["bullish"]), 1),
            "bearish": round(float(latest["bearish"]), 1),
            "neutral": round(float(latest["neutral"]), 1),
            "bull_bear_spread": round(float(latest["bullish"]) - float(latest["bearish"]), 1),
            "prev_week": {
                "bullish": round(float(prev_week["bullish"]), 1),
                "bearish": round(float(prev_week["bearish"]), 1),
                "neutral": round(float(prev_week["neutral"]), 1),
            },
            "historical_avg": {
                "bullish": hist_avg_bull,
                "bearish": hist_avg_bear,
            },
            "weeks_of_data": len(df),
        }

        print(f"  OK: Bull {result['bullish']}% / Bear {result['bearish']}% (spread: {result['bull_bear_spread']:+.1f}%)")
        return result

    except Exception as e:
        print(f"  ERROR: AAII fetch failed: {e}")
        return {}


# ============================================================
# Helpers
# ============================================================

def _calculate_comparisons(series):
    """
    Calculate period-over-period changes for a pandas Series.

    Returns dict like:
      { "1w": {"value": 4250.5, "change": +50.2, "change_pct": +1.2}, ... }
    """
    if series.empty:
        return {}

    latest_value = float(series.iloc[-1])
    comparisons = {}

    for period_name, lookback_days in COMPARISON_PERIODS.items():
        if len(series) > lookback_days:
            past_value = float(series.iloc[-(lookback_days + 1)])
            change = latest_value - past_value
            change_pct = (change / abs(past_value) * 100) if past_value != 0 else 0

            comparisons[period_name] = {
                "past_value": round(past_value, 4),
                "change": round(change, 4),
                "change_pct": round(change_pct, 2),
            }

    return comparisons


def save_results(data, filename):
    """Save collected data as JSON with metadata."""
    filepath = os.path.join(DATA_DIR, filename)
    output = {
        "collected_at": datetime.now().isoformat(),
        "data": data,
    }
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Saved: {filepath}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Collect market data from various sources")
    parser.add_argument("--source", choices=["fred", "yf", "cot", "aaii", "all"],
                        default="all", help="Which data source to fetch")
    args = parser.parse_args()

    ensure_dirs()
    print(f"Collecting data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.source in ("fred", "all"):
        fred_data = collect_fred()
        save_results(fred_data, "fred_data.json")
        print()

    if args.source in ("yf", "all"):
        yf_data = collect_yfinance()
        save_results(yf_data, "yfinance_data.json")
        print()

    if args.source in ("cot", "all"):
        cot_data = collect_cot()
        save_results(cot_data, "cot_data.json")
        print()

    if args.source in ("aaii", "all"):
        aaii_data = collect_aaii()
        save_results(aaii_data, "aaii_data.json")
        print()

    # Save metadata about this collection run
    metadata = {
        "last_run": datetime.now().isoformat(),
        "comparison_periods": COMPARISON_PERIODS,
        "sources_collected": args.source,
    }
    save_results(metadata, "metadata.json")

    print("=" * 60)
    print("Collection complete. Run 'python render.py' to generate dashboard.")


if __name__ == "__main__":
    main()
