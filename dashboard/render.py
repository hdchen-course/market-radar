"""
Dashboard HTML Renderer
========================
Reads collected JSON data and renders a static HTML dashboard.

No JavaScript frameworks needed — pure HTML/CSS with inline data.
Open output/dashboard.html in any browser.

Usage:
  python render.py              # render full dashboard
  python render.py --open       # render and open in browser
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from config import DATA_DIR, OUTPUT_DIR, COMPARISON_PERIODS


def load_data(filename):
    """Load a JSON data file. Returns empty dict if file missing or corrupt."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  WARN: {filepath} not found. Run 'python collect.py' first.")
        return {}
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  ERROR: Failed to read {filepath}: {e}")
        return {}


def format_number(value, decimals=2):
    """Format number with commas and sign for display."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 10_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.{decimals}f}"


def change_class(value):
    """Return CSS class based on positive/negative change."""
    if value is None or value == 0:
        return "neutral"
    return "positive" if value > 0 else "negative"


# ============================================================
# HTML Template (single-file, no external dependencies)
# ============================================================

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Data Dashboard — {{ generated_at }}</title>
<style>
  :root {
    --bg: #0f1419;
    --card-bg: #1a2332;
    --border: #2d3748;
    --text: #e2e8f0;
    --text-dim: #8899a6;
    --green: #00c853;
    --red: #ff1744;
    --gold: #ffd600;
    --blue: #448aff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, 'SF Mono', 'Fira Code', monospace; background: var(--bg); color: var(--text); padding: 1rem; font-size: 13px; }
  h1 { font-size: 1.3rem; color: var(--gold); margin-bottom: 0.25rem; }
  h2 { font-size: 1rem; color: var(--blue); margin: 1.5rem 0 0.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }
  h3 { font-size: 0.85rem; color: var(--text-dim); margin: 1rem 0 0.4rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .meta { color: var(--text-dim); font-size: 0.75rem; margin-bottom: 1rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.5rem; }
  .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 0.6rem 0.8rem; }
  .card-title { font-size: 0.75rem; color: var(--text-dim); margin-bottom: 0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card-value { font-size: 1.1rem; font-weight: 700; }
  .card-changes { display: flex; gap: 0.6rem; margin-top: 0.3rem; font-size: 0.7rem; }
  .change { padding: 0.1rem 0.3rem; border-radius: 3px; }
  .positive { color: var(--green); }
  .negative { color: var(--red); }
  .neutral { color: var(--text-dim); }
  .positive .change { background: rgba(0,200,83,0.1); }
  .negative .change { background: rgba(255,23,68,0.1); }

  /* COT table */
  table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; font-size: 0.8rem; }
  th, td { padding: 0.35rem 0.5rem; text-align: right; border-bottom: 1px solid var(--border); }
  th { color: var(--text-dim); font-weight: 600; text-align: left; }
  td:first-child { text-align: left; color: var(--text); font-weight: 500; }

  /* AAII gauge */
  .sentiment-bar { display: flex; height: 24px; border-radius: 4px; overflow: hidden; margin: 0.5rem 0; }
  .sentiment-bar .bull { background: var(--green); }
  .sentiment-bar .neutral-bar { background: var(--text-dim); }
  .sentiment-bar .bear { background: var(--red); }
  .sentiment-labels { display: flex; justify-content: space-between; font-size: 0.75rem; }

  .section { margin-bottom: 1.5rem; }
  .error-note { color: var(--red); font-size: 0.75rem; font-style: italic; }
  @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<h1>Market Data Dashboard</h1>
<p class="meta">Generated: {{ generated_at }} | Data from: {{ data_timestamp }} | Periods: 1W / 1M / 3M / 6M / 1Y</p>

{% if not has_data %}
<p class="error-note">No data files found. Run 'python collect.py' first.</p>
{% endif %}

<!-- ============ FRED: Liquidity & Yields ============ -->
{% if fred_data %}
{% for group_name, items in fred_grouped.items() %}
<div class="section">
<h2>{{ group_name | replace("_", " ") | title }}</h2>
{% for category, cat_items in items.items() %}
<h3>{{ category }}</h3>
<div class="grid">
{% for item in cat_items %}
<div class="card">
  <div class="card-title">{{ item.name }}</div>
  <div class="card-value">{{ item.latest_display }}</div>
  <div class="card-changes">
    {% for period, comp in item.comparisons.items() %}
    <span class="{{ comp.css_class }}"><span class="change">{{ period }}: {{ comp.display }}</span></span>
    {% endfor %}
  </div>
</div>
{% endfor %}
</div>
{% endfor %}
</div>
{% endfor %}
{% endif %}

<!-- ============ Yahoo Finance: Equities & Commodities ============ -->
{% if yf_data %}
{% for group_name, items in yf_grouped.items() %}
<div class="section">
<h2>{{ group_name | replace("_", " ") | title }}</h2>
{% for category, cat_items in items.items() %}
<h3>{{ category }}</h3>
<div class="grid">
{% for item in cat_items %}
<div class="card">
  <div class="card-title">{{ item.name }} ({{ item.ticker }})</div>
  <div class="card-value">${{ item.latest_price }} <span class="{{ item.daily_class }}" style="font-size:0.8rem">({{ item.daily_display }})</span></div>
  <div class="card-changes">
    {% for period, comp in item.comparisons.items() %}
    <span class="{{ comp.css_class }}"><span class="change">{{ period }}: {{ comp.display }}</span></span>
    {% endfor %}
  </div>
</div>
{% endfor %}
</div>
{% endfor %}
</div>
{% endfor %}
{% endif %}

<!-- ============ COT Positioning ============ -->
{% if cot_data %}
<div class="section">
<h2>CFTC Commitments of Traders (Positioning)</h2>
<table>
<tr><th>Contract</th><th>Net Speculative</th><th>% of OI</th><th>Net Commercial</th><th>Open Interest</th><th>Report Date</th></tr>
{% for item in cot_items %}
<tr>
  <td>{{ item.name }}</td>
  <td class="{{ item.spec_class }}">{{ item.net_spec_display }}</td>
  <td class="{{ item.spec_class }}">{{ item.spec_pct_oi }}%</td>
  <td>{{ item.net_comm_display }}</td>
  <td>{{ item.oi_display }}</td>
  <td>{{ item.report_date }}</td>
</tr>
{% endfor %}
</table>
</div>
{% endif %}

<!-- ============ AAII Sentiment ============ -->
{% if aaii_data %}
<div class="section">
<h2>AAII Investor Sentiment</h2>
{% if aaii_data.source == 'manual' %}
<div class="card" style="max-width:500px">
  <div class="card-title">Manual Check Required</div>
  <p style="margin:0.5rem 0">AAII blocks automated downloads.</p>
  <a href="{{ aaii_data.url }}" target="_blank" style="color:var(--accent)">Click here to view latest AAII data →</a>
</div>
{% else %}
<div class="card" style="max-width:500px">
  <div class="card-title">Survey Date: {{ aaii_data.latest_date }}</div>
  <div class="sentiment-bar">
    <div class="bull" style="width:{{ aaii_data.bullish }}%"></div>
    <div class="neutral-bar" style="width:{{ aaii_data.neutral }}%"></div>
    <div class="bear" style="width:{{ aaii_data.bearish }}%"></div>
  </div>
  <div class="sentiment-labels">
    <span class="positive">Bull: {{ aaii_data.bullish }}%</span>
    <span class="neutral">Neutral: {{ aaii_data.neutral }}%</span>
    <span class="negative">Bear: {{ aaii_data.bearish }}%</span>
  </div>
  <div style="margin-top:0.5rem; font-size:0.75rem; color:var(--text-dim)">
    Bull-Bear Spread: <span class="{{ 'positive' if aaii_data.bull_bear_spread > 0 else 'negative' }}">{{ aaii_data.bull_bear_spread }}%</span>
    &nbsp;|&nbsp; Hist Avg Bull: {{ aaii_data.historical_avg.bullish }}% / Bear: {{ aaii_data.historical_avg.bearish }}%
    {% if aaii_data.prev_week %}
    <br>Prior Week: Bull {{ aaii_data.prev_week.bullish }}% / Bear {{ aaii_data.prev_week.bearish }}%
    {% endif %}
  </div>
</div>
{% endif %}
</div>
{% endif %}

</body>
</html>
"""


# ============================================================
# Data Transformation (JSON → template-ready dicts)
# ============================================================

def prepare_fred_data(raw):
    """Group FRED data by group → category for template rendering."""
    if not raw or "data" not in raw:
        return {}

    grouped = {}
    for series_id, info in raw["data"].items():
        group = info.get("group", "other")
        category = info.get("category", "Other")

        if group not in grouped:
            grouped[group] = {}
        if category not in grouped[group]:
            grouped[group][category] = []

        # Format latest value
        latest = info.get("latest", {})
        latest_val = latest.get("value") if latest else None
        latest_display = format_number(latest_val) if latest_val is not None else "N/A"

        # Format comparisons
        comparisons = {}
        for period, comp in info.get("comparisons", {}).items():
            pct = comp.get("change_pct", 0)
            comparisons[period] = {
                "display": f"{pct:+.1f}%",
                "css_class": change_class(pct),
            }

        grouped[group][category].append({
            "series_id": series_id,
            "name": info["name"],
            "latest_display": latest_display,
            "comparisons": comparisons,
        })

    return grouped


def prepare_yf_data(raw):
    """Group Yahoo Finance data by group → category."""
    if not raw or "data" not in raw:
        return {}

    grouped = {}
    for ticker, info in raw["data"].items():
        group = info.get("group", "other")
        category = info.get("category", "Other")

        if group not in grouped:
            grouped[group] = {}
        if category not in grouped[group]:
            grouped[group][category] = []

        # Format comparisons
        comparisons = {}
        for period, comp in info.get("comparisons", {}).items():
            pct = comp.get("change_pct", 0)
            comparisons[period] = {
                "display": f"{pct:+.1f}%",
                "css_class": change_class(pct),
            }

        daily_pct = info.get("daily_change_pct", 0)

        grouped[group][category].append({
            "ticker": ticker,
            "name": info["name"],
            "latest_price": format_number(info.get("latest_price"), 2),
            "daily_display": f"{daily_pct:+.2f}%",
            "daily_class": change_class(daily_pct),
            "comparisons": comparisons,
        })

    return grouped


def prepare_cot_data(raw):
    """Prepare COT data for table rendering."""
    if not raw or "data" not in raw:
        return []

    items = []
    for code, info in raw["data"].items():
        net_spec = info.get("net_speculative", 0)
        items.append({
            "name": info["name"],
            "net_spec_display": f"{net_spec:+,}",
            "spec_class": change_class(net_spec),
            "spec_pct_oi": info.get("spec_pct_oi", 0),
            "net_comm_display": f"{info.get('net_commercial', 0):+,}",
            "oi_display": f"{info.get('open_interest', 0):,}",
            "report_date": info.get("report_date", ""),
        })

    return items


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Render market data dashboard HTML")
    parser.add_argument("--open", action="store_true", help="Open dashboard in browser after rendering")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading collected data...")
    fred_raw = load_data("fred_data.json")
    yf_raw = load_data("yfinance_data.json")
    cot_raw = load_data("cot_data.json")
    aaii_raw = load_data("aaii_data.json")

    # Determine data timestamp
    data_timestamp = "Unknown"
    for raw in [fred_raw, yf_raw, cot_raw, aaii_raw]:
        if raw and "collected_at" in raw:
            data_timestamp = raw["collected_at"][:19]
            break

    has_data = any([fred_raw, yf_raw, cot_raw, aaii_raw])

    # Prepare template data
    fred_grouped = prepare_fred_data(fred_raw)
    yf_grouped = prepare_yf_data(yf_raw)
    cot_items = prepare_cot_data(cot_raw)
    aaii_data = aaii_raw.get("data", {}) if aaii_raw else {}

    # Render HTML
    print("Rendering dashboard...")
    template = Template(DASHBOARD_TEMPLATE)
    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        data_timestamp=data_timestamp,
        has_data=has_data,
        fred_data=bool(fred_grouped),
        fred_grouped=fred_grouped,
        yf_data=bool(yf_grouped),
        yf_grouped=yf_grouped,
        cot_data=bool(cot_items),
        cot_items=cot_items,
        aaii_data=aaii_data if aaii_data else None,
    )

    output_path = os.path.join(OUTPUT_DIR, "dashboard.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard written to: {output_path}")

    if args.open:
        if platform.system() == "Darwin":
            subprocess.run(["open", output_path])
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", output_path])
        else:
            print(f"  Open manually: file://{os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()
