# Market Data Dashboard

Pure-data market dashboard. No LLM needed — just fetches numbers and shows them side-by-side with period comparisons.

## Quick Start

```bash
# One-time setup
chmod +x setup.sh && ./setup.sh

# Get a free FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html
export FRED_API_KEY=your_key_here

# Run
source venv/bin/activate
python collect.py          # fetch data (~30 seconds)
python render.py --open    # generate + open HTML dashboard
```

## What It Shows

| Section | Source | Data |
|---------|--------|------|
| Liquidity | FRED | Fed balance sheet, RRP, TGA, USD index |
| Yields | FRED | 5/10/30Y rates, yield curve spread |
| Inflation & Jobs | FRED | CPI, Core PCE, payrolls, jobless claims |
| Consumer | FRED | Disposable income, savings rate, consumer credit |
| Fear/Stress | FRED | VIX, TED spread, HY OAS, financial stress |
| Semiconductors | Yahoo Finance | NVDA, AMD, TSM, SOX, AI ETFs |
| Commodities | Yahoo Finance | Gold, Silver, Oil, Copper, Nat Gas |
| Indices & Bonds | Yahoo Finance | SPX, NDX, TLT, IEF, TIP |
| COT Positioning | CFTC | Net speculative/commercial for gold, silver, oil, etc. |
| Sentiment | AAII | Bull/bear/neutral survey + historical avg |

Every data point includes: **current value + 1W / 1M / 3M / 6M / 1Y change**.

## Configuration

Edit `config.py` to add/remove series, tickers, or change comparison periods.

## Files

```
dashboard/
├── setup.sh           # one-time venv + pip install
├── config.py          # all data sources and settings
├── collect.py         # data fetcher (FRED, yfinance, CFTC, AAII)
├── render.py          # HTML generator (Jinja2 template)
├── requirements.txt   # Python dependencies
├── .gitignore         # excludes venv/, data/, output/
├── data/              # (generated) JSON files from collect.py
└── output/            # (generated) dashboard.html
```
