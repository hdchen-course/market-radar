# 盤面判讀引擎 `radar.py` + 多尺度 CVD `cvd_multi.py`

> ⚠️ **規則化客觀工具，非投資建議。** 輸出一致、可重複、可分享，但**不取代情境判讀**
> ——當天的財報、指數調整(如 MSCI)、政策/地緣催化、突發新聞，規則抓不到，那一層仍需
> 人工或 LLM 補。本引擎定位是「客觀儀表板 + 劇本骨架」，不是神奇買賣點。

## 這是什麼

給一個標的，整合多個客觀訊號 → 輸出三段：**數據面板 → 解讀劇本(偏多/偏空各列「為什麼」) → 需要盯哪些數據**。
目的是把盤面分析的「客觀計算層」固化成**可反覆跑、輸出一致**的引擎（消除每次手算的解讀飄移），順便方便分享。

## 怎麼跑（純標準庫，無需安裝套件）

```bash
python3 radar.py BTCUSDT          # 幣安永續（真 CVD）
python3 radar.py ETHUSDT --spot   # 幣安現貨
python3 radar.py NVDAUSDT         # 幣安美股鏡像（代表性打折，見下）
python3 cvd_multi.py BTCUSDT      # 只看多尺度 CVD（radar 的子模組，可單獨用）
```

`radar.py` 依賴同目錄的 `cvd_multi.py`，分享時兩支一起帶。

## 搭配免費 LLM 交叉判讀（補情境層、免錢）

radar 是 local 客觀規則層，**抓不到當日催化**（財報/指數調整/地緣/新聞）。把輸出丟給免費雲端 LLM 補情境：

```bash
python3 radar.py BTCUSDT --prompt > req.md
```

把 `req.md` 貼給 **免費版 ChatGPT / Gemini / Grok**，它會補當日新聞/催化、給偏多/區間/偏空三劇本機率、指出規則初判可能被推翻之處。
= **local 客觀一致（radar）+ 雲端 LLM 情境（免費）**，兩層都有、不用付費 API。

## 整合哪些訊號

| 模組 | 看什麼 |
|---|---|
| 多尺度 CVD | 結構 1d / 中期 4h / 近期 1h / 當下 15m 的主動成交量差，判「價格 vs 主動資金」背離 |
| Volume Profile | POC（最大量價位）/ Value Area 上下緣（真實成交量堆積＝支撐壓力） |
| SuperTrend(300,3) | 日/4h/1h 三框共振（多/空/盤整） |
| funding / OI | 加密永續的擁擠度（過熱易殺多、轉負＝空頭擁擠可軋空） |
| 宏觀背景層 | 10Y 殖利率 / DXY / VIX / HY 信用利差；對風險/無息資產的順逆風 |
| K 線形態 | 錘子 / 射擊之星 / 十字星 / 大實體 / 多空吞沒（公開標準定義自寫、純 python；單根形態須配合位置，僅輔助不主導） |

## 輸出三段

1. **客觀面板**：報價、VP 籌碼區、SuperTrend 三框、funding/OI、宏觀背景、CVD 規則判讀。
2. **解讀劇本**：主劇本（偏多 / 區間 / 偏空）＋ 偏多與偏空**各自「為什麼」**（列出支持它的客觀訊號）。
3. **需要盯哪些數據**：多方確認 / 空方確認 / 情境層（規則抓不到、需人工補）。

## CVD 能不能用在美股？

- **幣安永續 / 現貨**：有 `takerBuyBase` 欄位 → **真 CVD**。
- **幣安美股鏡像**（`NVDAUSDT`/`TSMUSDT` 等）：有 taker → 可算，但量小、是鏡像 order flow，**代表性打折**。
- **美股本尊**（Yahoo）：只有 OHLCV、無主動買賣分解 → **算不出真 CVD**。`cvd_multi.py --yahoo` 提供「紅K量=買、黑K量=賣」的 **proxy**（標 `[PROXY]`），僅粗略方向參考。真 CVD 要付費 tick data。

## 限制（誠實）

- 規則計分是**「大致」判讀**；閾值（VIX 18/20、funding 0.01%、Value Area 70% 等）是經驗值，**會因市況/標的失準**。
- **不含情境催化**（財報/指數調整/地緣/新聞）——那層需人工或 LLM。
- 宏觀逆風框架（殖利率↑、美元↑、VIX↑、HY↑＝逆風）對「風險/無息資產」大致適用，**個別資產需人工微調**。

## 測試

```bash
python3 test_cvd_multi.py   # CVD 規則(合成確定性) + 今年真實資料 smoke(需網路)
python3 test_radar.py       # 劇本引擎規則(合成 fixture 確定性)
```

## 資料來源（全免費）

Binance `fapi`/`api`（報價 / K線 / funding / OI）、Yahoo（殖利率 / DXY / VIX）、FRED（HY 信用利差 `BAMLH0A0HYM2`，無需 key）。
