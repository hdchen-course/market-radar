#!/usr/bin/env python3
"""多尺度 CVD（累積主動成交量差）分析工具。

同時計算一個標的在多個時間框架（結構/中期/近期/當下）的 CVD，判斷
「價格方向 vs 主動資金方向」是否背離——這是單一框架看不出來的
（長線派發、短線止穩可以並存）。本機執行時沒有 LLM 在旁解讀，故內建
規則化 interpret()，直接輸出一句可行動的結論，不只印數字。

資料來源：
  - binance 永續 (fapi) / 現貨 (spot)：有 takerBuyBase，可算「真 CVD」
    （主動 delta = 2 * 主動買量 − 總量）。
  - yahoo（美股本尊）：免費 OHLCV 無主動買賣分解，只能用「紅K量=買 / 黑K量=賣」
    的粗略 proxy（標 [PROXY]），非真 CVD，僅供參考。

用法：
  python3 cvd_multi.py BTCUSDT          # 幣安永續，真 CVD
  python3 cvd_multi.py BTCUSDT --spot   # 幣安現貨，真 CVD
  python3 cvd_multi.py NVDAUSDT         # 幣安美股鏡像永續（代表性打折）
  python3 cvd_multi.py NVDA --yahoo     # 美股本尊，proxy CVD（不準）
"""
import argparse
import json
import sys
import urllib.request

# 每個時間框架：(標籤, interval, 取樣根數)，刻意涵蓋 結構→當下。
BINANCE_TIMEFRAMES = [
    ("結構 1d", "1d", 60),
    ("中期 4h", "4h", 42),    # ~7 天
    ("近期 1h", "1h", 48),    # ~2 天
    ("當下 15m", "15m", 48),  # ~12 小時
]
# Yahoo intraday 的 range 上限不同（15m ~60 天、1h ~730 天），逐尺度給合理 range。
YAHOO_TIMEFRAMES = [
    ("結構 1d", "1d", "3mo"),
    ("中期 1h", "1h", "1mo"),
    ("當下 15m", "15m", "5d"),
]
# interpret() 取「最短的成功尺度」當當下，優先序由短到長。
_SHORTEST_FIRST = ["當下 15m", "近期 1h", "中期 4h", "中期 1h", "結構 1d"]
_MIN_BARS = 4
_UA = {"User-Agent": "Mozilla/5.0"}
_TIMEOUT = 20


def _get_json(url):
    """抓 URL 回傳解析後的 JSON；呼叫端負責捕捉例外。"""
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.load(resp)


def fetch_binance(symbol, interval, limit, use_spot=False):
    """回傳 [(close, taker_delta, volume), ...]，taker_delta 為真實主動 delta。"""
    base = "https://api.binance.com/api/v3" if use_spot else "https://fapi.binance.com/fapi/v1"
    url = f"{base}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    rows = []
    for k in _get_json(url):
        close = float(k[4])
        volume = float(k[5])
        taker_buy = float(k[9])               # 主動買進成交量（吃賣方掛單）
        taker_delta = 2 * taker_buy - volume  # = 主動買 − 主動賣
        rows.append((close, taker_delta, volume))
    return rows


def fetch_yahoo(symbol, interval, range_):
    """回傳 [(close, proxy_delta, volume), ...]。

    免費 OHLCV 無主動買賣分解，用紅/黑 K 當 proxy：收漲→量記為買、收跌→量記為賣。
    這不是真 CVD，只是粗略方向代理。
    """
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?range={range_}&interval={interval}")
    result = _get_json(url)["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    opens, closes, vols = quote["open"], quote["close"], quote["volume"]
    rows = []
    for open_, close, vol in zip(opens, closes, vols):
        if open_ is None or close is None or vol is None:
            continue
        proxy_delta = vol if close >= open_ else -vol
        rows.append((close, proxy_delta, vol))
    return rows


def summarize_scale(rows):
    """把一組 K 棒濃縮成：價格變化%、淨 CVD、前半 CVD、後半 CVD。"""
    net_cvd = sum(delta for _, delta, _ in rows)
    price_change_pct = (rows[-1][0] / rows[0][0] - 1) * 100
    mid = len(rows) // 2
    cvd_first = sum(delta for _, delta, _ in rows[:mid])
    cvd_last = sum(delta for _, delta, _ in rows[mid:])
    return price_change_pct, net_cvd, cvd_first, cvd_last


def classify_turn(cvd_first, cvd_last):
    """用前半/後半 CVD 判斷近期主動資金方向有沒有轉向。"""
    if cvd_first < 0 <= cvd_last:
        return "後半轉流入↑"
    if cvd_first > 0 >= cvd_last:
        return "後半轉流出↓"
    return "持續流入" if cvd_last > 0 else "持續流出"


def interpret(results, is_proxy):
    """套規則輸出一句可行動結論（本機無 LLM 解讀時用）。

    results: {框架標籤: (price_pct, net_cvd, cvd_first, cvd_last)}
    規則：1d 定「結構性質」(派發/吸籌/健康)，最短尺度定「短線時機」，再合成。
    """
    structure = results.get("結構 1d")
    shortest = next((results[k] for k in _SHORTEST_FIRST if k in results), None)
    if structure is None or shortest is None:
        print("\n[自動判讀] 資料不足，無法歸納。")
        return

    price_up = structure[0] > 0
    cvd_inflow = structure[1] > 0
    if price_up and not cvd_inflow:
        nature = "頂背離：價漲但主動資金流出＝派發，中期偏空逆風"
    elif not price_up and cvd_inflow:
        nature = "底背離：價跌但主動資金流入＝吸籌，中期偏多"
    elif price_up and cvd_inflow:
        nature = "健康上漲：價漲且資金流入"
    else:
        nature = "健康下跌：價跌且資金流出"

    turn = classify_turn(shortest[2], shortest[3])
    short_is_buy = turn in ("後半轉流入↑", "持續流入")  # 短線主動資金偏買
    if turn == "後半轉流入↑":
        timing = "短線賣壓衰竭/買盤回歸（可能短彈或止穩）"
    elif turn == "後半轉流出↓":
        timing = "短線買盤轉弱/賣壓轉強（留意加速下跌）"
    elif turn == "持續流入":
        timing = "短線持續買進"
    else:
        timing = "短線持續賣出"

    is_top = "頂背離" in nature
    is_bottom = "底背離" in nature
    if is_top and short_is_buy:
        combo = "中期派發但短線買盤回來=區間/反彈：別追多(上有壓)也別追空(下有撐)，等長短同向"
    elif is_top and not short_is_buy:
        combo = "中期派發 + 短線續賣＝偏空，反彈到上緣視為出貨/空點"
    elif is_bottom and not short_is_buy:
        combo = "中期吸籌但短線續賣=區間/打底：別追空，等短線轉買確認"
    elif is_bottom and short_is_buy:
        combo = "中期吸籌 + 短線轉買＝偏多，回下緣視為承接點"
    elif short_is_buy:
        combo = "長短同向偏多，順勢但注意過熱"
    else:
        combo = "長短同向偏空，順勢但注意超賣"

    tag = "（proxy，僅參考）" if is_proxy else ""
    print(f"\n[自動判讀]{tag}")
    print(f"  結構性質：{nature}")
    print(f"  短線時機：{timing}")
    print(f"  綜合：{combo}")


def run(symbol, source, use_spot):
    """跑完所有時間框架、印表格、呼叫 interpret。回傳是否至少一個尺度成功。"""
    is_proxy = source == "yahoo"
    label = "美股本尊 proxy（非真CVD）" if is_proxy else ("幣安現貨" if use_spot else "幣安永續")
    print(f"=== {symbol} 多尺度 CVD（{label}）===")
    if is_proxy:
        print("  ⚠ Yahoo 無主動買賣分解，以下為紅/黑K proxy、僅粗略方向參考，非真 CVD。")
    print(f"{'框架':<12}{'價格變化':>11}{'淨CVD':>12}{'前半':>11}{'後半':>11}  近期轉向")

    timeframes = YAHOO_TIMEFRAMES if is_proxy else BINANCE_TIMEFRAMES
    results = {}
    for row in timeframes:
        label_tf = row[0]
        try:
            if is_proxy:
                bars = fetch_yahoo(symbol, row[1], row[2])
            else:
                bars = fetch_binance(symbol, row[1], row[2], use_spot)
            if len(bars) < _MIN_BARS:
                print(f"{label_tf:<12}  資料不足，跳過")
                continue
            pct, net, first, last = summarize_scale(bars)
            results[label_tf] = (pct, net, first, last)
            print(f"{label_tf:<12}{pct:>+10.1f}%{net:>+12.0f}{first:>+11.0f}{last:>+11.0f}  {classify_turn(first, last)}")
        except Exception as exc:  # 單一尺度失敗不擋其他尺度
            print(f"{label_tf:<12}  取得失敗：{exc}")

    interpret(results, is_proxy)
    return bool(results)


def main(argv=None):
    parser = argparse.ArgumentParser(description="多尺度 CVD 分析")
    parser.add_argument("symbol", help="標的代碼，如 BTCUSDT / NVDAUSDT / NVDA")
    parser.add_argument("--spot", action="store_true", help="用幣安現貨（預設永續）")
    parser.add_argument("--yahoo", action="store_true", help="用 Yahoo 美股本尊（proxy，非真CVD）")
    args = parser.parse_args(argv)
    source = "yahoo" if args.yahoo else "binance"
    return 0 if run(args.symbol, source, args.spot) else 1


if __name__ == "__main__":
    sys.exit(main())
