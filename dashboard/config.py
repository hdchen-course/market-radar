"""
Configuration for Market Data Dashboard.

All data sources, series IDs, and display settings are defined here.
Edit this file to add/remove indicators without touching collection logic.
"""

import os

# ============================================================
# API Keys
# ============================================================
# FRED (Federal Reserve Economic Data) - free key from:
# https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# ============================================================
# FRED Series - Macro Liquidity
# Each entry: (series_id, display_name, category)
# ============================================================
FRED_SERIES = {
    "liquidity": [
        ("WALCL", "Fed Balance Sheet (Total Assets)", "Fed Balance Sheet"),
        ("RRPONTSYD", "Reverse Repo (ON RRP)", "Liquidity Drain"),
        ("WTREGEN", "Treasury General Account (TGA)", "Liquidity Drain"),
        ("WDTGAL", "TGA - Deposits", "Liquidity Drain"),
        ("DGS5", "5-Year Treasury Yield", "Yields"),
        ("DGS10", "10-Year Treasury Yield", "Yields"),
        ("DGS30", "30-Year Treasury Yield", "Yields"),
        ("T10Y2Y", "10Y-2Y Spread (Yield Curve)", "Yields"),
        ("DTWEXBGS", "Trade Weighted USD Index (Broad)", "Dollar"),
        ("DEXUSEU", "EUR/USD Exchange Rate", "Dollar"),
    ],
    "inflation_employment": [
        ("CPIAUCSL", "CPI All Items (SA)", "Inflation"),
        ("CPILFESL", "Core CPI (ex Food & Energy)", "Inflation"),
        ("PCEPILFE", "Core PCE Price Index", "Inflation"),
        ("UNRATE", "Unemployment Rate", "Employment"),
        ("PAYEMS", "Nonfarm Payrolls", "Employment"),
        ("ICSA", "Initial Jobless Claims (Weekly)", "Employment"),
    ],
    "consumer_household": [
        ("DSPIC96", "Real Disposable Personal Income", "Consumer"),
        ("PSAVERT", "Personal Savings Rate %", "Consumer"),
        ("TOTALSL", "Total Consumer Credit", "Consumer"),
        ("UMCSENT", "UMich Consumer Sentiment", "Sentiment"),
        ("MORTGAGE30US", "30-Year Mortgage Rate", "Housing"),
    ],
    "fear_stress": [
        ("VIXCLS", "VIX (CBOE Volatility Index)", "Fear"),
        ("TEDRATE", "TED Spread", "Credit Stress"),
        ("BAMLH0A0HYM2", "High Yield OAS Spread", "Credit Stress"),
        ("STLFSI4", "St. Louis Financial Stress Index", "Stress"),
    ],
}

# ============================================================
# Yahoo Finance Tickers
# (ticker, display_name, category)
# ============================================================
YFINANCE_TICKERS = {
    "semiconductors": [
        ("NVDA", "NVIDIA", "AI Semis"),
        ("AMD", "AMD", "AI Semis"),
        ("TSM", "TSMC", "AI Semis"),
        ("AVGO", "Broadcom", "AI Semis"),
        ("^SOX", "SOX Semiconductor Index", "Sector Index"),
        ("SMH", "VanEck Semiconductor ETF", "Sector ETF"),
        ("BOTZ", "Global X Robotics & AI ETF", "AI ETF"),
    ],
    "commodities_precious": [
        ("GC=F", "Gold Futures", "Precious Metals"),
        ("SI=F", "Silver Futures", "Precious Metals"),
        ("GDX", "Gold Miners ETF", "Precious Metals"),
        ("CL=F", "WTI Crude Oil", "Energy"),
        ("NG=F", "Natural Gas", "Energy"),
        ("HG=F", "Copper Futures", "Industrial Metals"),
    ],
    "indices_bonds": [
        ("^GSPC", "S&P 500", "US Equity"),
        ("^IXIC", "NASDAQ Composite", "US Equity"),
        ("^DJI", "Dow Jones", "US Equity"),
        ("TLT", "20+ Year Treasury Bond ETF", "Bonds"),
        ("IEF", "7-10 Year Treasury Bond ETF", "Bonds"),
        ("SHY", "1-3 Year Treasury Bond ETF", "Bonds"),
        ("TIP", "TIPS Bond ETF", "Inflation Protected"),
    ],
}

# ============================================================
# CFTC Commitments of Traders (COT) Report
# Fetched from CFTC website / Quandl
# (contract_code, display_name, category)
# ============================================================
COT_CONTRACTS = [
    ("088691", "Gold (COMEX)", "Precious Metals"),
    ("084691", "Silver (COMEX)", "Precious Metals"),
    ("099741", "Crude Oil (NYMEX)", "Energy"),
    ("096742", "Natural Gas (NYMEX)", "Energy"),
    ("098662", "Copper (COMEX)", "Industrial Metals"),
    ("099741", "S&P 500 (CME)", "Equity Index"),
    ("232741", "US Dollar Index (ICE)", "Currency"),
    ("099741", "10-Year Treasury Note", "Bonds"),
]

# ============================================================
# AAII Sentiment Survey
# Source: https://www.aaii.com/sentimentsurvey
# ============================================================
AAII_URL = "https://www.aaii.com/files/surveys/sentiment.xls"

# ============================================================
# Comparison Periods
# How far back to look for period-over-period comparisons
# ============================================================
COMPARISON_PERIODS = {
    "1w": 5,      # 5 trading days
    "1m": 21,     # ~1 month
    "3m": 63,     # ~3 months
    "6m": 126,    # ~6 months
    "1y": 252,    # ~1 year
}

# ============================================================
# Output
# ============================================================
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
