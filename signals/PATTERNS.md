# patterns.py — 純標準庫 K 線型態判讀（TA-Lib CDL* 替代）

零第三方相依的蠟燭型態辨識，取代需編譯 C 底層、安裝不易的 TA-Lib。
涵蓋 **TA-Lib 全部 61 個 CDL\* ＋ 5 個常用 extras ＝ 66 型態**。

## 為什麼

TA-Lib 卡在 C 編譯；但 K 線型態本質只是「實體／上下影線／跳空／前後根關係／所處趨勢」
的幾何比大小，純 Python 即可，與本專案 `signals/` 的純標準庫路線一致。

## 安裝

無需安裝。`import patterns`（檔案放在 `signals/`）。Python 3.x 標準庫即可。

## 用法

```python
import patterns as P

bars = [(open, high, low, close), ...]          # 由舊到新

# 1) 高階：最後一根觸發的型態（含中文名、方向、說明）
P.detect_last(bars)
# -> [('錘子線', 'bull', '跌勢末端長下影=低檔承接'), ...]    bias ∈ {bull,bear,neutral}

# 2) 最後一根的 TA-Lib 風格訊號（只列非 0）
P.scan(bars)            # -> {'CDLHAMMER': 100, 'CDLDOJI': 100}

# 3) 整條序列每型態的訊號陣列
P.scan_all(bars)        # -> {'CDLHAMMER': [0,0,...,100], ...}

# 4) TA-Lib 相容（drop-in）：陣列進、與輸入等長的整數序列出（+100 多 / -100 空 / 0 無）
o = [b[0] for b in bars]; h = [b[1] for b in bars]
l = [b[2] for b in bars]; c = [b[3] for b in bars]
P.CDLENGULFING(o, h, l, c)      # -> [..., -100, 0, 100, ...]
```

多數情況 `import talib` → `import patterns as talib` 可直接替換（已實作的 CDL\* 子集）。

## 設計特性

- **正確**：型態定義經獨立紅隊（3 組，單根／雙根／三根+四五根）對照 TA-Lib 演算法＋Nison/Bulkowski
  逐一稽核並修正；`test_patterns.py` 84 項測試（66 個逐型態正向 fixture ＋ 不變量 ＋ 易混淆對照）全綠。
- **高效能**：OHLC 衍生量（實體/影線/全距/顏色）在 `_Ctx` 建構時一次算好；每型態為單點函式
  `_impl(x, i)`。`scan` 建 1 次 ctx、每型態只算最後一根 → 約 **0.08 ms/次**（66 型態、長序列）。
- **記憶體安全**：不修改輸入、無全域可變狀態（登錄表於 import 時建好）、全程 list/float、無遞迴深度風險；
  OHLC 長度不一致會丟 `ValueError`；空輸入安全回空。
- **易用**：四種 API（detect_last / scan / scan_all / CDL\* drop-in）；門檻集中於 `PARAMS` 可調。

## TA-Lib 相容性註記（號誌差異）

本庫對帶明確多空語義的型態回傳**方向號誌**，少數與 TA-Lib 的「純出現旗標」不同：

| 型態 | 本庫 | TA-Lib | 說明 |
|------|------|--------|------|
| CDLGRAVESTONEDOJI | **-100** | +100 | 墓碑十字＝高檔遭壓＝偏空（語義更正確） |

需要嚴格 TA-Lib「是否出現」語義者，請改用 `abs(signal) != 0` 判定。
CDLDRAGONFLYDOJI / CDLTAKURI 方向與 TA-Lib 同為 +100，不受影響。

## 定義基準與限制

- 門檻以「近 N 根平均實體／當根全距」的相對比例實作（概念對應 TA-Lib 的 CandleSetting，
  非其全域 SMA，語義等價、可在 `PARAMS` 調校）。
- 反轉型態（錘子/吊人/星…）內建前趨勢條件（`trend()`，近 10 根收盤 SMA）。
- **回測／樣本外驗證未做**；型態訊號當客觀底稿，非進場依據。

## 測試

```bash
python3 test_patterns.py     # 純標準庫，不需 venv；全綠回傳 0
```

## 66 型態清單

單根(18)：Doji, DojiStar, DragonflyDoji, GravestoneDoji, LongLeggedDoji, RickshawMan,
HighWave, SpinningTop, Marubozu, ClosingMarubozu, LongLine, ShortLine, BeltHold,
Hammer, InvertedHammer, HangingMan, ShootingStar, Takuri。
雙根(17)：Engulfing, Harami, HaramiCross, Piercing, DarkCloudCover, HomingPigeon,
MatchingLow, OnNeck, InNeck, Thrusting, SeparatingLines, Kicking, KickingByLength,
CounterAttack, +extras: TweezerTop, TweezerBottom, RisingWindow, FallingWindow, MatchingHigh。
三根：MorningStar, EveningStar, MorningDojiStar, EveningDojiStar, TriStar, 3WhiteSoldiers,
3BlackCrows, Identical3Crows, 3Inside, 3Outside, AdvanceBlock, StalledPattern, 2Crows,
UpsideGap2Crows, 3StarsInSouth, Unique3River, TasukiGap, StickSandwich, Hikkake, HikkakeMod。
四/五根：3LineStrike, ConcealBabySwall, LadderBottom, MatHold, RiseFall3Methods,
XSideGap3Methods, GapSideSideWhite, Breakaway, AbandonedBaby。
