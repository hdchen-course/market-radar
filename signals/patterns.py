"""patterns.py — 純標準庫 K 線型態判讀（TA-Lib CDL* 的完整替代，零第三方相依）。

設計目標：正確、易用、高效能、記憶體安全、文件完整。

為什麼有這支：TA-Lib 需編譯 C 底層、安裝不易；蠟燭型態本質只是
「實體 / 上下影線 / 跳空 / 前後根關係 / 所處趨勢」的幾何比大小，純 Python 即可。

覆蓋：TA-Lib 全部 61 個 CDL* 函式（名稱一致）＋ 5 個常用 extras
（鑷頂 / 鑷底 / 上升窗 / 下降窗 / 高價配）＝ 66 型態。

兩種 API：
  1) TA-Lib 相容（drop-in）：`CDLENGULFING(open_, high, low, close) -> list[int]`
     回傳與輸入等長整數序列，慣例同 TA-Lib：+100=多方、-100=空方、0=無。
     （純中性型態如 Doji / HighWave / 長腿十字 回傳 +100 代表「出現」，方向另判。）
  2) 高階：`detect_last(bars)->[(name,bias,note)]`、`scan(bars)->{CDLNAME:±100}`、`scan_all(bars)`
     bars = [(open, high, low, close), ...]（與 radar.detect_candles 同格式）。

效能/記憶體：
  - 每檔 OHLC 的衍生量（實體 / 影線 / 全距 / 顏色）在 `_Ctx` 建構時一次算好（O(n)）。
  - 每個型態的核心是單點函式 `_impl(x, i)`（只看第 i 根及其回看窗，O(1)~O(window)）。
  - 公開 `CDL*` 掃全長＝建 1 次 ctx + n 次單點判定；`scan/detect_last` 建 1 次 ctx、
    每型態只算最後一根 → 不重複建 ctx、不重算整條陣列（這是相對 naive 版的主要加速）。
  - 不修改輸入、無全域可變狀態（登錄表於 import 時建好）、全程 list/float，無遞迴深度風險。

TA-Lib 相容性註記：本庫對「帶明確多空語義」的型態回傳方向號誌（+100 多 / -100 空），
故少數 TA-Lib 以 +100 當「純出現旗標」的型態，本庫會回方向號：
  - CDLGRAVESTONEDOJI：TA-Lib 回 +100（出現），本庫回 -100（墓碑=高檔遭壓=偏空，語義更正確）。
  （CDLDRAGONFLYDOJI / CDLTAKURI 方向與 TA-Lib 同為 +100，不受影響。）
需要嚴格 TA-Lib 號誌者請改以 `abs(signal)!=0` 判「是否出現」。

定義基準：以 TA-Lib 演算法為主（本庫目標＝取代 TA-Lib），輔以 Nison/Bulkowski 標準。
門檻（長/短實體、doji、長/短影、跳空…）集中於 PARAMS，概念對應 TA-Lib 的 CandleSetting，
以「近 N 根平均實體 / 當根全距」為基準的相對比例實作（語義等價、可調）。
回測/樣本外驗證未做；當客觀底稿，非進場依據。
"""
from __future__ import annotations

PARAMS = {
    "doji_body": 0.10,          # 實體 <= 全距 * 此 → doji
    "near": 0.10,               # 兩價「相等」容差（佔當根全距比例）
    "shadow_very_long": 2.0,    # 影線 >= 實體 * 此 → 很長影（錘子類）
    "shadow_short": 0.30,       # 影線 <= 全距 * 此 → 短影
    "shadow_very_short": 0.10,  # 影線 <= 全距 * 此 → 幾無影
    "body_long": 1.3,           # 實體 >= 近N均實體 * 此 → 長實體
    "body_short": 0.5,          # 實體 <= 近N均實體 * 此 → 短實體
    "marubozu": 0.90,           # 實體 >= 全距 * 此 → 光頭光腳
    "equal": 0.05,              # 兩值「幾乎相等」容差（佔均實體比例）
    "trend_n": 10,              # 前趨勢回看根數
    "body_avg_n": 10,           # 均實體回看根數
}


# ---------- 前處理：衍生量一次算好 ----------
class _Ctx:
    """把 OHLC 轉成常用衍生量並快取；所有型態單點函式吃這個 context。"""
    __slots__ = ("o", "h", "l", "c", "n", "body", "up", "dn", "rng", "white", "black")

    def __init__(self, open_, high, low, close):
        n = len(close)
        if not (len(open_) == len(high) == len(low) == n):
            raise ValueError("open/high/low/close 長度必須一致")
        self.o, self.h, self.l, self.c, self.n = open_, high, low, close, n
        self.body = [abs(close[i] - open_[i]) for i in range(n)]
        self.up = [high[i] - (open_[i] if open_[i] > close[i] else close[i]) for i in range(n)]
        self.dn = [(open_[i] if open_[i] < close[i] else close[i]) - low[i] for i in range(n)]
        self.rng = [(high[i] - low[i]) or 1e-9 for i in range(n)]
        self.white = [close[i] > open_[i] for i in range(n)]
        self.black = [close[i] < open_[i] for i in range(n)]

    def avgbody(self, i):
        n = PARAMS["body_avg_n"]
        lo = i - n if i - n > 0 else 0
        if i <= lo:
            return self.body[i] or 1e-9
        s = 0.0
        for k in range(lo, i):
            s += self.body[k]
        return (s / (i - lo)) or 1e-9

    def long_body(self, i):
        return self.body[i] >= self.avgbody(i) * PARAMS["body_long"]

    def short_body(self, i):
        return self.body[i] <= self.avgbody(i) * PARAMS["body_short"]

    def doji(self, i):
        return self.body[i] <= self.rng[i] * PARAMS["doji_body"]

    def marubozu(self, i):
        # 形狀定義：幾無上下影 + 實體佔滿全距（不含「長實體」要求，供需短 marubozu
        # 的型態如 3starsinsouth 共用；需長 marubozu 者各自再加 long_body）。
        vs = PARAMS["shadow_very_short"]
        return (self.up[i] <= self.rng[i] * vs and self.dn[i] <= self.rng[i] * vs
                and self.body[i] >= self.rng[i] * PARAMS["marubozu"])

    def trend(self, i):
        """第 i 根相對前 n 根收盤均價：+1 升 / -1 降 / 0 平。"""
        n = PARAMS["trend_n"]
        lo = i - n if i - n > 0 else 0
        if i - lo < 2:
            return 0
        sma = sum(self.c[lo:i]) / (i - lo)
        tol = (max(self.h[lo:i]) - min(self.l[lo:i])) * 0.02
        if self.c[i] > sma + tol:
            return 1
        if self.c[i] < sma - tol:
            return -1
        return 0

    def gap_up(self, i):   # 第 i 根實體完全在 i-1 實體上方
        return min(self.o[i], self.c[i]) > max(self.o[i - 1], self.c[i - 1])

    def gap_dn(self, i):
        return max(self.o[i], self.c[i]) < min(self.o[i - 1], self.c[i - 1])


# ---------- 登錄表 + 單點函式裝飾器 ----------
# name -> (impl(x,i)->int, 中文, 說明, 是否純中性, 需要回看根數)
_IMPLS = []
_BY_NAME = {}


def _reg(name, zh, note, neutral=False, lookback=0):
    def deco(fn):
        entry = (name, fn, zh, note, neutral, lookback)
        _IMPLS.append(entry)
        _BY_NAME[name] = entry
        return fn
    return deco


# =========================================================================
# 單根
# =========================================================================
@_reg("CDLDOJI", "十字星", "開收極近=猶豫變盤", neutral=True)
def _doji(x, i):
    return 100 if x.doji(i) else 0


@_reg("CDLDOJISTAR", "星形十字", "長實體後跳空doji=反轉前兆", lookback=1)
def _dojistar(x, i):
    if i < 1 or not (x.long_body(i - 1) and x.doji(i)):
        return 0
    if x.black[i - 1] and x.gap_dn(i):
        return 100
    if x.white[i - 1] and x.gap_up(i):
        return -100
    return 0


@_reg("CDLDRAGONFLYDOJI", "蜻蜓十字", "長下影+貼高=低檔承接")
def _dragonfly(x, i):
    if x.doji(i) and x.up[i] <= x.rng[i] * PARAMS["shadow_very_short"] and x.dn[i] >= x.rng[i] * 0.6:
        return 100
    return 0


@_reg("CDLGRAVESTONEDOJI", "墓碑十字", "長上影+貼低=高檔遭壓")
def _gravestone(x, i):
    if x.doji(i) and x.dn[i] <= x.rng[i] * PARAMS["shadow_very_short"] and x.up[i] >= x.rng[i] * 0.6:
        return -100
    return 0


@_reg("CDLLONGLEGGEDDOJI", "長腿十字", "長上下影=劇烈猶豫", neutral=True)
def _longlegged(x, i):
    if x.doji(i) and x.up[i] >= x.rng[i] * 0.3 and x.dn[i] >= x.rng[i] * 0.3:
        return 100
    return 0


@_reg("CDLRICKSHAWMAN", "黃包車夫", "長腿十字實體居中=猶豫", neutral=True)
def _rickshaw(x, i):
    mid_body = (x.o[i] + x.c[i]) / 2
    center = x.l[i] + x.rng[i] * 0.5
    if (x.doji(i) and x.up[i] >= x.rng[i] * 0.3 and x.dn[i] >= x.rng[i] * 0.3
            and abs(mid_body - center) <= x.rng[i] * 0.15):
        return 100
    return 0


@_reg("CDLHIGHWAVE", "高浪線", "短實體+很長上下影=方向迷失")
def _highwave(x, i):
    if (x.short_body(i) and not x.doji(i)
            and x.up[i] >= x.rng[i] * 0.4 and x.dn[i] >= x.rng[i] * 0.4):
        return 100 if x.white[i] else -100
    return 0


@_reg("CDLSPINNINGTOP", "紡錘線", "小實體+長上下影=動能衰竭")
def _spinningtop(x, i):
    if (not x.doji(i) and x.body[i] <= x.rng[i] * 0.3
            and x.up[i] >= x.body[i] and x.dn[i] >= x.body[i]):
        return 100 if x.white[i] else -100
    return 0


@_reg("CDLMARUBOZU", "光頭光腳", "幾無影線=單邊強勢")
def _marubozu(x, i):
    if x.marubozu(i) and x.long_body(i):   # TA-Lib：光頭光腳須為長實體
        return 100 if x.white[i] else -100
    return 0


@_reg("CDLCLOSINGMARUBOZU", "收盤光頭光腳", "收盤端無影=收盤強勢")
def _closingmarubozu(x, i):
    if not x.long_body(i):
        return 0
    vs = x.rng[i] * PARAMS["shadow_very_short"]
    if x.white[i] and x.up[i] <= vs:
        return 100
    if x.black[i] and x.dn[i] <= vs:
        return -100
    return 0


@_reg("CDLLONGLINE", "長線", "長實體短影=趨勢強")
def _longline(x, i):
    if (x.long_body(i) and x.up[i] <= x.rng[i] * PARAMS["shadow_short"]
            and x.dn[i] <= x.rng[i] * PARAMS["shadow_short"]):
        return 100 if x.white[i] else -100
    return 0


@_reg("CDLSHORTLINE", "短線", "短實體短影=盤整")
def _shortline(x, i):
    if (x.short_body(i) and x.up[i] <= x.rng[i] * PARAMS["shadow_short"]
            and x.dn[i] <= x.rng[i] * PARAMS["shadow_short"]):
        return 100 if x.white[i] else -100
    return 0


@_reg("CDLBELTHOLD", "捉腰帶", "開盤端無影長實體=反轉起手")
def _belthold(x, i):
    if not x.long_body(i):
        return 0
    vs = x.rng[i] * PARAMS["shadow_very_short"]
    if x.white[i] and x.dn[i] <= vs:
        return 100
    if x.black[i] and x.up[i] <= vs:
        return -100
    return 0


@_reg("CDLHAMMER", "錘子線", "跌勢末端長下影=低檔承接")
def _hammer(x, i):
    if (x.dn[i] >= x.body[i] * PARAMS["shadow_very_long"] and x.up[i] <= x.rng[i] * PARAMS["shadow_very_short"]
            and not x.doji(i) and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLINVERTEDHAMMER", "倒錘子線", "跌勢末端長上影=偏多(需確認)")
def _invhammer(x, i):
    if (x.up[i] >= x.body[i] * PARAMS["shadow_very_long"] and x.dn[i] <= x.rng[i] * PARAMS["shadow_very_short"]
            and not x.doji(i) and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLHANGINGMAN", "吊人線", "漲勢末端長下影=高檔動搖")
def _hangingman(x, i):
    if (x.dn[i] >= x.body[i] * PARAMS["shadow_very_long"] and x.up[i] <= x.rng[i] * PARAMS["shadow_very_short"]
            and not x.doji(i) and x.trend(i) > 0):
        return -100
    return 0


@_reg("CDLSHOOTINGSTAR", "射擊之星", "漲勢末端長上影=高檔遭壓")
def _shootingstar(x, i):
    if (x.up[i] >= x.body[i] * PARAMS["shadow_very_long"] and x.dn[i] <= x.rng[i] * PARAMS["shadow_very_short"]
            and not x.doji(i) and x.trend(i) > 0):
        return -100
    return 0


@_reg("CDLTAKURI", "探水竿", "極長下影蜻蜓=強力低接")
def _takuri(x, i):
    if (x.doji(i) and x.up[i] <= x.rng[i] * PARAMS["shadow_very_short"]
            and x.dn[i] >= x.body[i] * 3 and x.dn[i] >= x.rng[i] * 0.7):
        return 100
    return 0


# =========================================================================
# 雙根
# =========================================================================
@_reg("CDLENGULFING", "吞沒", "今實體包昨實體=反方反攻", lookback=1)
def _engulfing(x, i):
    if i < 1:
        return 0
    o, c, po, pc = x.o[i], x.c[i], x.o[i - 1], x.c[i - 1]
    if c > o and pc < po and c >= po and o <= pc:
        return 100
    if c < o and pc > po and o >= pc and c <= po:
        return -100
    return 0


@_reg("CDLHARAMI", "母子", "小實體被長實體包=動能衰竭", lookback=1)
def _harami(x, i):
    if i < 1 or not (x.long_body(i - 1) and x.short_body(i)):
        return 0
    hi, lo = max(x.o[i], x.c[i]), min(x.o[i], x.c[i])
    phi, plo = max(x.o[i - 1], x.c[i - 1]), min(x.o[i - 1], x.c[i - 1])
    if hi <= phi and lo >= plo and (phi - plo) > 0:
        return 100 if x.black[i - 1] else -100   # 母子方向 = −前根顏色（TA-Lib），第二根顏色不限
    return 0


@_reg("CDLHARAMICROSS", "母子十字", "第二根doji的母子=變盤更強", lookback=1)
def _haramicross(x, i):
    if i < 1 or not (x.doji(i) and x.long_body(i - 1)):
        return 0
    hi, lo = max(x.o[i], x.c[i]), min(x.o[i], x.c[i])
    phi, plo = max(x.o[i - 1], x.c[i - 1]), min(x.o[i - 1], x.c[i - 1])
    if hi <= phi and lo >= plo and (phi - plo) > 0:
        return 100 if x.black[i - 1] else -100
    return 0


@_reg("CDLPIERCING", "貫穿線", "前黑今紅收過中點=底部反轉", lookback=1)
def _piercing(x, i):
    if i < 1:
        return 0
    mid = (x.o[i - 1] + x.c[i - 1]) / 2
    if x.black[i - 1] and x.long_body(i - 1) and x.white[i] and x.o[i] < x.l[i - 1] and mid < x.c[i] < x.o[i - 1]:
        return 100
    return 0


@_reg("CDLDARKCLOUDCOVER", "烏雲蓋頂", "前紅今黑收破中點=頂部反轉", lookback=1)
def _darkcloud(x, i):
    if i < 1:
        return 0
    mid = (x.o[i - 1] + x.c[i - 1]) / 2
    if x.white[i - 1] and x.long_body(i - 1) and x.black[i] and x.o[i] > x.h[i - 1] and x.o[i - 1] < x.c[i] < mid:
        return -100
    return 0


@_reg("CDLHOMINGPIGEON", "信鴿", "跌勢兩黑母子=偏多反轉", lookback=1)
def _homingpigeon(x, i):
    if i < 1:
        return 0
    if (x.black[i - 1] and x.black[i] and x.long_body(i - 1) and x.short_body(i)
            and max(x.o[i], x.c[i]) <= x.o[i - 1] and min(x.o[i], x.c[i]) >= x.c[i - 1]
            and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLMATCHINGLOW", "低價配", "兩黑同收盤=支撐", lookback=1)
def _matchinglow(x, i):
    if i < 1:
        return 0
    if (x.black[i - 1] and x.black[i]
            and abs(x.c[i] - x.c[i - 1]) <= x.avgbody(i) * PARAMS["equal"] and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLONNECK", "頸上線", "反彈到前根低=弱勢續跌", lookback=1)
def _onneck(x, i):
    if i < 1:
        return 0
    if (x.black[i - 1] and x.long_body(i - 1) and x.white[i] and x.o[i] < x.l[i - 1]
            and abs(x.c[i] - x.l[i - 1]) <= x.avgbody(i) * PARAMS["equal"] and x.trend(i) < 0):
        return -100
    return 0


@_reg("CDLINNECK", "頸內線", "反彈略入前實體=弱勢續跌", lookback=1)
def _inneck(x, i):
    if i < 1:
        return 0
    if (x.black[i - 1] and x.long_body(i - 1) and x.white[i] and x.o[i] < x.l[i - 1]
            and x.c[i - 1] <= x.c[i] <= x.c[i - 1] + x.avgbody(i) * 0.1 and x.trend(i) < 0):
        return -100
    return 0


@_reg("CDLTHRUSTING", "插入線", "反彈未過中點=續跌", lookback=1)
def _thrusting(x, i):
    if i < 1:
        return 0
    mid = (x.o[i - 1] + x.c[i - 1]) / 2
    if (x.black[i - 1] and x.long_body(i - 1) and x.white[i] and x.o[i] < x.l[i - 1]
            and x.c[i - 1] + x.avgbody(i) * PARAMS["equal"] < x.c[i] < mid and x.trend(i) < 0):
        return -100
    return 0


@_reg("CDLSEPARATINGLINES", "分手線", "同開盤反色=順勢續行", lookback=1)
def _separating(x, i):
    if i < 1:
        return 0
    if not (abs(x.o[i] - x.o[i - 1]) <= x.avgbody(i) * PARAMS["equal"] and x.long_body(i)):
        return 0
    if x.black[i - 1] and x.white[i] and x.trend(i) > 0:
        return 100
    if x.white[i - 1] and x.black[i] and x.trend(i) < 0:
        return -100
    return 0


@_reg("CDLKICKING", "反沖", "反色marubozu跳空=強反轉", lookback=1)
def _kicking(x, i):
    if i < 1 or not (x.marubozu(i - 1) and x.marubozu(i)):
        return 0
    if x.black[i - 1] and x.white[i] and x.l[i] > x.h[i - 1]:
        return 100
    if x.white[i - 1] and x.black[i] and x.h[i] < x.l[i - 1]:
        return -100
    return 0


@_reg("CDLKICKINGBYLENGTH", "反沖(長度定向)", "反沖+長根定方向", lookback=1)
def _kickingbylength(x, i):
    if i < 1 or not (x.marubozu(i - 1) and x.marubozu(i)):
        return 0
    longer = i if x.body[i] >= x.body[i - 1] else i - 1   # 方向由「較長的 marubozu」顏色決定
    sign = 100 if x.white[longer] else -100
    if x.black[i - 1] and x.white[i] and x.l[i] > x.h[i - 1]:
        return sign
    if x.white[i - 1] and x.black[i] and x.h[i] < x.l[i - 1]:
        return sign
    return 0


@_reg("CDLCOUNTERATTACK", "反擊線", "反色長實體同收盤=反轉", lookback=1)
def _counterattack(x, i):
    if i < 1 or not (x.long_body(i - 1) and x.long_body(i)):
        return 0
    if abs(x.c[i] - x.c[i - 1]) > x.avgbody(i) * PARAMS["equal"]:
        return 0
    if x.black[i - 1] and x.white[i] and x.trend(i) < 0:
        return 100
    if x.white[i - 1] and x.black[i] and x.trend(i) > 0:
        return -100
    return 0


# =========================================================================
# 三根
# =========================================================================
@_reg("CDLMORNINGSTAR", "晨星", "長黑+星+長紅=底部反轉", lookback=2)
def _morningstar(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.black[a] and x.long_body(a) and x.short_body(s) and max(x.o[s], x.c[s]) < x.c[a]
            and x.white[i] and x.c[i] > (x.o[a] + x.c[a]) / 2):   # 收過第一根實體中點（無上限，不漏強勢晨星）
        return 100
    return 0


@_reg("CDLEVENINGSTAR", "夜星", "長紅+星+長黑=頂部反轉", lookback=2)
def _eveningstar(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.white[a] and x.long_body(a) and x.short_body(s) and min(x.o[s], x.c[s]) > x.c[a]
            and x.black[i] and x.c[i] < (x.o[a] + x.c[a]) / 2):   # 收破第一根實體中點（無下限）
        return -100
    return 0


@_reg("CDLMORNINGDOJISTAR", "晨星十字", "星為doji的晨星=更強底", lookback=2)
def _morningdojistar(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.black[a] and x.long_body(a) and x.doji(s) and max(x.o[s], x.c[s]) < x.c[a]
            and x.white[i] and x.c[i] > (x.o[a] + x.c[a]) / 2):
        return 100
    return 0


@_reg("CDLEVENINGDOJISTAR", "夜星十字", "星為doji的夜星=更強頂", lookback=2)
def _eveningdojistar(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.white[a] and x.long_body(a) and x.doji(s) and min(x.o[s], x.c[s]) > x.c[a]
            and x.black[i] and x.c[i] < (x.o[a] + x.c[a]) / 2):
        return -100
    return 0


@_reg("CDLTRISTAR", "三星", "連三doji中間跳空=變盤", lookback=2)
def _tristar(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if not (x.doji(a) and x.doji(s) and x.doji(i)):
        return 0
    sb = (x.o[s], x.c[s])
    if min(sb) > max(x.o[a], x.c[a]) and min(sb) > max(x.o[i], x.c[i]):
        return -100
    if max(sb) < min(x.o[a], x.c[a]) and max(sb) < min(x.o[i], x.c[i]):
        return 100
    return 0


@_reg("CDL3WHITESOLDIERS", "紅三兵", "連三長紅收高=強多", lookback=2)
def _3whitesoldiers(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1

    def solid(j):
        return x.white[j] and x.long_body(j) and x.up[j] <= x.rng[j] * PARAMS["shadow_short"]
    if (solid(a) and solid(b) and solid(i) and x.c[b] > x.c[a] and x.c[i] > x.c[b]
            and x.c[a] > x.o[b] > x.o[a] and x.c[b] > x.o[i] > x.o[b]):
        return 100
    return 0


@_reg("CDL3BLACKCROWS", "黑三鴉", "連三長黑收低=強空", lookback=2)
def _3blackcrows(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1

    def solid(j):
        return x.black[j] and x.long_body(j) and x.dn[j] <= x.rng[j] * PARAMS["shadow_short"]
    if (solid(a) and solid(b) and solid(i) and x.c[b] < x.c[a] and x.c[i] < x.c[b]
            and x.o[a] > x.o[b] > x.c[a] and x.o[b] > x.o[i] > x.c[b]):
        return -100
    return 0


@_reg("CDLIDENTICAL3CROWS", "三胞胎烏鴉", "三黑開=前收=更強空", lookback=2)
def _identical3crows(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1

    def solid(j):
        return x.black[j] and x.long_body(j)
    if (solid(a) and solid(b) and solid(i) and x.c[b] < x.c[a] and x.c[i] < x.c[b]
            and abs(x.o[b] - x.c[a]) <= x.avgbody(i) * PARAMS["equal"]
            and abs(x.o[i] - x.c[b]) <= x.avgbody(i) * PARAMS["equal"]):
        return -100
    return 0


@_reg("CDL3INSIDE", "三內部", "母子+確認根=反轉確認", lookback=2)
def _3inside(x, i):
    if i < 2:
        return 0
    h = _harami(x, i - 1)   # 確認根收破第一根（母根）開盤＝TA-Lib 定義
    if h == 100 and x.white[i] and x.c[i] > x.o[i - 2]:
        return 100
    if h == -100 and x.black[i] and x.c[i] < x.o[i - 2]:
        return -100
    return 0


@_reg("CDL3OUTSIDE", "三外部", "吞沒+順勢確認=反轉確認", lookback=2)
def _3outside(x, i):
    if i < 2:
        return 0
    e = _engulfing(x, i - 1)
    if e == 100 and x.c[i] > x.c[i - 1]:
        return 100
    if e == -100 and x.c[i] < x.c[i - 1]:
        return -100
    return 0


@_reg("CDLADVANCEBLOCK", "前進阻擋", "三白漸縮上影長=漲勢衰竭", lookback=2)
def _advanceblock(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.white[a] and x.white[b] and x.white[i] and x.c[b] > x.c[a] and x.c[i] > x.c[b]
            and x.o[a] < x.o[b] < x.c[a] and x.o[b] < x.o[i] < x.c[b]
            and ((x.body[i] < x.body[b] < x.body[a]) or x.up[i] >= x.body[i] or x.up[b] >= x.body[b])
            and x.trend(i) > 0):   # 衰竭=實體遞縮 OR 長上影（TA-Lib 為 OR）
        return -100
    return 0


@_reg("CDLSTALLEDPATTERN", "停頓型態", "兩長白後小白停滯=偏空", lookback=2)
def _stalled(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.white[a] and x.white[b] and x.white[i] and x.long_body(a) and x.long_body(b)
            and x.c[b] > x.c[a] and x.short_body(i)
            and x.o[i] >= x.c[b] - x.body[b] * 0.5 and x.c[i] > x.c[b] and x.trend(i) > 0):
        return -100
    return 0


@_reg("CDL2CROWS", "雙鴉", "漲勢跳空黑回補=偏空", lookback=2)
def _2crows(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.white[a] and x.long_body(a) and x.black[s] and min(x.o[s], x.c[s]) > x.c[a]
            and x.black[i] and x.c[s] < x.o[i] < x.o[s] and x.o[a] < x.c[i] < x.c[a] and x.trend(i) > 0):
        return -100
    return 0


@_reg("CDLUPSIDEGAP2CROWS", "向上跳空雙鴉", "跳空兩黑=偏空", lookback=2)
def _upsidegap2crows(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.white[a] and x.long_body(a) and x.black[s] and x.black[i]
            and min(x.o[s], x.c[s]) > x.c[a]
            and x.o[i] > x.o[s] and x.c[i] < x.c[s] and x.c[i] > x.c[a] and x.trend(i) > 0):
        return -100
    return 0


@_reg("CDL3STARSINSOUTH", "南方三星", "跌勢三黑漸縮=衰竭偏多", lookback=2)
def _3starsinsouth(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.black[a] and x.long_body(a) and x.dn[a] >= x.body[a]
            and x.black[b] and x.o[a] > x.o[b] > x.c[a] and x.l[b] > x.l[a]
            and x.black[i] and x.marubozu(i) and x.short_body(i)
            and x.h[i] <= x.h[b] and x.l[i] >= x.l[b] and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLUNIQUE3RIVER", "獨特三河床", "長黑+新低harami+小白=偏多", lookback=2)
def _unique3river(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.black[a] and x.long_body(a) and x.black[b]
            and x.o[b] <= x.o[a] and x.c[b] >= x.c[a] and x.l[b] < x.l[a]
            and x.white[i] and x.short_body(i) and x.o[i] < x.c[b]
            and x.c[i] < x.c[b] + x.avgbody(i) and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLTASUKIGAP", "墊襯跳空", "跳空未補=續勢", lookback=2)
def _tasukigap(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.white[a] and x.white[b] and x.gap_up(b) and x.black[i]
            and min(x.o[b], x.c[b]) < x.o[i] < x.c[b] and x.c[i] < x.o[b] and x.c[i] > x.c[a]):
        return 100
    if (x.black[a] and x.black[b] and x.gap_dn(b) and x.white[i]
            and x.c[b] < x.o[i] < max(x.o[b], x.c[b]) and x.c[i] > x.o[b] and x.c[i] < x.c[a]):
        return -100
    return 0


@_reg("CDLSTICKSANDWICH", "條形三明治", "兩黑夾白同收盤=支撐偏多", lookback=2)
def _sticksandwich(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.black[a] and x.white[b] and x.black[i]
            and abs(x.c[i] - x.c[a]) <= x.avgbody(i) * PARAMS["equal"]
            and x.l[b] > x.c[a] and x.o[i] > x.c[b] and x.trend(i) < 0):   # 中間白低點高於首收、第三黑開在白收之上
        return 100
    return 0


@_reg("CDLHIKKAKE", "Hikkake陷阱", "內困月假突破=反轉", lookback=2)
def _hikkake(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if not (x.h[b] < x.h[a] and x.l[b] > x.l[a]):   # 需 inside bar
        return 0
    if x.h[i] < x.h[b] and x.l[i] < x.l[b]:
        return 100
    if x.l[i] > x.l[b] and x.h[i] > x.h[b]:
        return -100
    return 0


@_reg("CDLHIKKAKEMOD", "修正Hikkake", "帶setup的Hikkake", lookback=3)
def _hikkakemod(x, i):
    if i < 3:
        return 0
    h = _hikkake(x, i)
    if h == 100 and x.c[i - 3] > x.c[i - 2]:
        return 100
    if h == -100 and x.c[i - 3] < x.c[i - 2]:
        return -100
    return 0


# =========================================================================
# 四/五根
# =========================================================================
@_reg("CDL3LINESTRIKE", "三線打擊", "三順勢後反色吞沒=續勢", lookback=3)
def _3linestrike(x, i):
    if i < 3:
        return 0
    a, b, c3 = i - 3, i - 2, i - 1
    if (x.white[a] and x.white[b] and x.white[c3] and x.c[b] > x.c[a] and x.c[c3] > x.c[b]
            and x.black[i] and x.o[i] > x.c[c3] and x.c[i] < x.o[a]):
        return 100
    if (x.black[a] and x.black[b] and x.black[c3] and x.c[b] < x.c[a] and x.c[c3] < x.c[b]
            and x.white[i] and x.o[i] < x.c[c3] and x.c[i] > x.o[a]):
        return -100
    return 0


@_reg("CDLCONCEALBABYSWALL", "藏嬰吞沒", "跌勢四黑末吞沒=偏多(罕)", lookback=3)
def _concealbaby(x, i):
    if i < 3:
        return 0
    a, b, c3 = i - 3, i - 2, i - 1
    if (x.black[a] and x.marubozu(a) and x.black[b] and x.marubozu(b)
            and x.black[c3] and x.up[c3] > 0 and x.o[c3] < x.c[b]
            and x.black[i] and x.h[i] > x.h[c3] and x.l[i] < x.l[c3] and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLLADDERBOTTOM", "梯底", "三長黑+上影黑+開高白=偏多", lookback=4)
def _ladderbottom(x, i):
    if i < 4:
        return 0
    a, b, c3, d = i - 4, i - 3, i - 2, i - 1
    if (x.black[a] and x.black[b] and x.black[c3]
            and x.o[a] > x.o[b] > x.c[a] and x.o[b] > x.o[c3] > x.c[b]
            and x.c[b] < x.c[a] and x.c[c3] < x.c[b]
            and x.black[d] and x.up[d] >= x.body[d] * 0.5
            and x.white[i] and x.o[i] > x.o[d] and x.trend(i) < 0):
        return 100
    return 0


@_reg("CDLMATHOLD", "鋪墊", "長白+回落三根+長白創高=續多", lookback=4)
def _mathold(x, i):
    if i < 4:
        return 0
    a, b, c3, d = i - 4, i - 3, i - 2, i - 1
    if (x.white[a] and x.long_body(a) and x.gap_up(b)
            and x.short_body(b) and x.short_body(c3) and x.short_body(d)   # 回落三根須真為小實體
            and min(x.c[b], x.c[c3], x.c[d]) > x.o[a] and x.c[d] < x.c[b]
            and x.white[i] and x.long_body(i) and x.c[i] > max(x.h[b], x.h[c3], x.h[d])):
        return 100
    return 0


@_reg("CDLRISEFALL3METHODS", "上升/下降三法", "長實體+反向三小+同向長=續勢", lookback=4)
def _risefall3(x, i):
    if i < 4:
        return 0
    a, b, c3, d = i - 4, i - 3, i - 2, i - 1
    hi3 = max(x.h[b], x.h[c3], x.h[d])
    lo3 = min(x.l[b], x.l[c3], x.l[d])
    if (x.white[a] and x.long_body(a) and x.black[b] and x.black[c3] and x.black[d]
            and hi3 <= x.h[a] and lo3 >= x.l[a]
            and x.white[i] and x.long_body(i) and x.c[i] > x.c[a] and x.o[i] > x.c[d]):
        return 100
    if (x.black[a] and x.long_body(a) and x.white[b] and x.white[c3] and x.white[d]
            and hi3 <= x.h[a] and lo3 >= x.l[a]
            and x.black[i] and x.long_body(i) and x.c[i] < x.c[a] and x.o[i] < x.c[d]):
        return -100
    return 0


@_reg("CDLXSIDEGAP3METHODS", "跳空三法", "跳空後補缺口=續勢", lookback=2)
def _xsidegap3(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if (x.white[a] and x.white[b] and x.gap_up(b) and x.black[i]
            and min(x.o[b], x.c[b]) < x.o[i] < max(x.o[b], x.c[b])   # 開在第2實體內
            and x.o[a] < x.c[i] < x.c[a]):                          # 收在第1根(白)實體內=補缺口
        return 100
    if (x.black[a] and x.black[b] and x.gap_dn(b) and x.white[i]
            and min(x.o[b], x.c[b]) < x.o[i] < max(x.o[b], x.c[b])
            and x.c[a] < x.c[i] < x.o[a]):                          # 收在第1根(黑)實體內
        return -100
    return 0


@_reg("CDLGAPSIDESIDEWHITE", "並列陽線跳空", "跳空後同色並列=續勢", lookback=2)
def _gapsidesidewhite(x, i):
    if i < 2:
        return 0
    a, b = i - 2, i - 1
    if not (abs(x.o[i] - x.o[b]) <= x.avgbody(i) * 0.3
            and abs(x.body[i] - x.body[b]) <= x.avgbody(i) * 0.5):
        return 0
    if x.gap_up(b) and x.white[b] and x.white[i]:
        return 100
    if x.gap_dn(b) and x.white[b] and x.white[i]:   # GAPSIDESIDE*WHITE*：兩種情況皆兩白，由跳空方向定號
        return -100
    return 0


@_reg("CDLBREAKAWAY", "脫離", "跳空順勢三根後反向大根=反轉", lookback=4)
def _breakaway(x, i):
    if i < 4:
        return 0
    a, b, c3, d = i - 4, i - 3, i - 2, i - 1
    if (x.black[a] and x.long_body(a) and x.gap_dn(b) and x.black[b]
            and x.c[c3] < x.c[b] and x.black[d] and x.c[d] < x.c[c3]
            and x.white[i] and x.long_body(i) and max(x.o[b], x.c[b]) < x.c[i] < x.c[a]):
        return 100
    if (x.white[a] and x.long_body(a) and x.gap_up(b) and x.white[b]
            and x.c[c3] > x.c[b] and x.white[d] and x.c[d] > x.c[c3]
            and x.black[i] and x.long_body(i) and x.c[a] < x.c[i] < min(x.o[b], x.c[b])):
        return -100
    return 0


@_reg("CDLABANDONEDBABY", "棄嬰", "孤立跳空doji=強反轉", lookback=2)
def _abandonedbaby(x, i):
    if i < 2:
        return 0
    a, s = i - 2, i - 1
    if (x.black[a] and x.long_body(a) and x.doji(s) and x.h[s] < x.l[a]
            and x.white[i] and x.l[i] > x.h[s] and x.c[i] > (x.o[a] + x.c[a]) / 2):
        return 100
    if (x.white[a] and x.long_body(a) and x.doji(s) and x.l[s] > x.h[a]
            and x.black[i] and x.h[i] < x.l[s] and x.c[i] < (x.o[a] + x.c[a]) / 2):
        return -100
    return 0


# ---------- extras（非 TA-Lib，但為常見標準型態）----------
@_reg("CDLTWEEZERTOP", "鑷頂", "兩根同高+漲勢=見頂(extra)", lookback=1)
def _tweezertop(x, i):
    if i < 1:
        return 0
    if abs(x.h[i] - x.h[i - 1]) <= x.rng[i] * PARAMS["near"] and x.trend(i) > 0:
        return -100
    return 0


@_reg("CDLTWEEZERBOTTOM", "鑷底", "兩根同低+跌勢=見底(extra)", lookback=1)
def _tweezerbottom(x, i):
    if i < 1:
        return 0
    if abs(x.l[i] - x.l[i - 1]) <= x.rng[i] * PARAMS["near"] and x.trend(i) < 0:
        return 100
    return 0


@_reg("CDLRISINGWINDOW", "上升窗", "向上跳空缺口=支撐續多(extra)", lookback=1)
def _risingwindow(x, i):
    if i < 1:
        return 0
    if x.l[i] > x.h[i - 1]:   # 真缺口（非實體跳空）
        return 100
    return 0


@_reg("CDLFALLINGWINDOW", "下降窗", "向下跳空缺口=壓力續空(extra)", lookback=1)
def _fallingwindow(x, i):
    if i < 1:
        return 0
    if x.h[i] < x.l[i - 1]:
        return -100
    return 0


@_reg("CDLMATCHINGHIGH", "高價配", "兩白同收盤=壓力(extra)", lookback=1)
def _matchinghigh(x, i):
    if i < 1:
        return 0
    if (x.white[i - 1] and x.white[i]
            and abs(x.c[i] - x.c[i - 1]) <= x.avgbody(i) * PARAMS["equal"] and x.trend(i) > 0):
        return -100
    return 0


# =========================================================================
# 公開 API
# =========================================================================
def _make_public(name, fn):
    def pub(open_, high, low, close):
        x = _Ctx(open_, high, low, close)
        return [fn(x, i) for i in range(x.n)]
    pub.__name__ = name
    pub.__qualname__ = name
    pub.__doc__ = f"{name}：TA-Lib 相容。回傳與輸入等長的 list[int]（+100/-100/0）。"
    return pub


# 於 import 時把每個 impl 包成 TA-Lib 相容的公開函式掛到模組命名空間
for _name, _fn, _zh, _note, _neu, _lb in _IMPLS:
    globals()[_name] = _make_public(_name, _fn)

# 所有公開型態名稱（供 iteration / 文件）
FUNCS = [e[0] for e in _IMPLS]


def _cols(bars):
    o = [b[0] for b in bars]; h = [b[1] for b in bars]
    l = [b[2] for b in bars]; c = [b[3] for b in bars]
    return o, h, l, c


def detect_last(bars):
    """回「最後一根」觸發的型態清單 [(中文名, bias, 說明)]；bias∈{bull,bear,neutral}。
    高效：只建 1 次 ctx、每型態只算最後一根。"""
    if not bars:
        return []
    x = _Ctx(*_cols(bars))
    last = x.n - 1
    out = []
    for name, fn, zh, note, neutral, _lb in _IMPLS:
        v = fn(x, last)
        if v == 0:
            continue
        bias = "neutral" if neutral else ("bull" if v > 0 else "bear")
        out.append((zh, bias, note))
    return out


def scan(bars):
    """回「最後一根」每型態 TA-Lib 風格訊號 {CDLNAME: +100/-100}（只列非 0）。"""
    if not bars:
        return {}
    x = _Ctx(*_cols(bars))
    last = x.n - 1
    res = {}
    for name, fn, _zh, _note, _neu, _lb in _IMPLS:
        v = fn(x, last)
        if v:
            res[name] = v
    return res


def scan_all(bars):
    """回整條序列每型態的 TA-Lib 風格陣列 {CDLNAME: [±100/0,...]}（建 1 次 ctx）。"""
    if not bars:
        return {}
    x = _Ctx(*_cols(bars))
    return {name: [fn(x, i) for i in range(x.n)] for name, fn, _z, _n, _nu, _lb in _IMPLS}


def pattern_count():
    return len(_IMPLS)
