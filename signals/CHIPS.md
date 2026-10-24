# 籌碼/成本分布工具：options_maxpain.py（股票）＋ urpd.py（BTC）

純標準庫、零第三方相依，與 `signals/` 既有路線（radar.py / vpvr.py / patterns.py）一致。
用來回答「BTC / MSTR 籌碼分布」——兩者籌碼來源不同，分兩支工具。

---

## 1. options_maxpain.py — 股票選擇權籌碼（MSTR 等）

股票沒有鏈上持幣，**選擇權 open interest 分布**是最接近「持倉/籌碼分布」的公開資料。

資料源：**CBOE 延遲報價**（免認證，含 OI / volume / IV / gamma / delta，需跟隨 307 重導）
`https://cdn.cboe.com/api/global/delayed_quotes/options/{SYMBOL}.json`

輸出：
- **Max Pain**：到期時讓所有未平倉選擇權買方「總內在價值賠付最小」的結算價＝常被引為到期磁吸(pin)價。
  頭條用**最近到期**單一到期（跨到期混算對任一到期都不成立，只當合算參考另列）。
- **OI 牆**：call OI 最大履約價（上方壓力/磁吸）、put OI 最大履約價（下方支撐）。
- **PCR**：put/call 比（OI 與 volume 兩種）。
- **Gamma 牆 + 淨 GEX（近似）**：做市商 gamma 曝險集中價位 + 正/負 γ regime 粗判。

```bash
python3 options_maxpain.py MSTR --expiries 3        # 文字
python3 options_maxpain.py MSTR --html               # 可貼進報告的 <div class="opt-box">
```
```python
import options_maxpain as om
spot, rows = om.fetch_cboe("MSTR")
res = om.analyze(spot, rows, expiries=3)
print(om.summary_text(res))
```

誠實鐵則（寫在程式 docstring）：CBOE 為**延遲**報價、OI 為 **T+1 結算**，只反映報價日持倉結構，
非即時、非進場訊號；Max Pain 是機械計算值不是預測；淨 GEX 的正負號繫於「做市商 long call/short put」
的無法驗證假設，只當量級/集中價位參考，不當精確美元值。

---

## 2. urpd.py — BTC 成本分布代理（URPD proxy）

真 URPD（UTXO Realized Price Distribution，每個價位有多少 BTC「最後一次鏈上移動」）需全 UTXO 集，
只有 Glassnode / CryptoQuant / CoinGlass 等（多付費）。本工具是**交易所成交量成本代理**：
在一段視窗上跑 Volume Profile（重用 vpvr 核心），把成交量在價位上的堆積當「成本簇」的代理。

資料源：Binance SPOT 週線，用 **quote volume（USD 名目，kline[7]）** 加權。

### 紅隊校正（2026-10-24）後的關鍵設計
1. 用 **quote volume(USD)** 而非 base(BTC) 量——否則早年廉價幣的巨大 BTC 周轉會把 POC 機械釘在週期低點。
2. **預設只看當前週期短窗（weekly×200≈近 4 年）**——全歷史線性 bin 在 3k→80k 拋物線上會壓扁 POC、
   並讓 below% 恆趨近 100%。看全歷史請加大 `--limit`。
3. `--log` 對數價格 bin，跨多倍數長視窗較公平。

### below%/above% 的硬性 caveat
它是「**本視窗內、成交量-時間加權**」的現價上下占比，**不是真實持幣成本分布**。
對長期上升資產，現價接近 ATH 時 below% 會機械趨近 100%（趨勢綁架，換 log bin 也救不了），
**不可與 Glassnode URPD 的「供給在獲利 %」類比**。只在現價位於視窗中段時較有參考性。

```bash
python3 urpd.py BTCUSDT                       # 預設 200 週、quote-vol
python3 urpd.py BTCUSDT --limit 480 --log     # 全歷史、對數 bin
python3 urpd.py BTCUSDT --html                 # <div class="urpd-box">
```
```python
import urpd
H, L, C, QV, span = urpd.fetch_binance_history("BTCUSDT", "1w", 200)
res = urpd.urpd(H, L, C, QV, bins=50)         # 另有 log=True
print(urpd.summary_text(res, span))
```

輸出：POC（最大成本簇）、VA（70% 價值區）、HVN（成本密集帶/支撐壓力）、LVN（成本真空帶/快速穿越）、
現價相對 POC 的多空結構、below%/above%（見 caveat）。

---

## 測試
```bash
python3 test_options_maxpain.py     # parse_occ/max_pain 手算反例/walls/pcr/gex/分析/不變量
python3 test_urpd.py                # 供給分割/成本簇/log-bin/空輸入/長度不符/不修改輸入
```

## 兩者皆非進場訊號
Volume Profile / 選擇權結構為**客觀結構底稿**，回測未做；與報告的情境判讀並陳，不強行統一。
鏈上真 URPD、13F 機構持倉、short interest 等仍需外部（多付費）資料源，本工具不涵蓋。
