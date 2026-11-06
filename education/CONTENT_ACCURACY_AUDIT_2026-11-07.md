# 教育內容正確性審查報告

- **審查日期**：2026-11-07（CST）
- **審查範圍**：`education/` 目前 23 個 HTML，其中 21 個教材頁、`trade_home.html` 首頁、`index.html` 導向頁；另檢查互動測驗文字與主要計算器公式。
- **目的**：交給 Claude 依優先順序修正內容。這是內容正確性審查，不是投資、稅務、法律或醫療建議。
- **工作樹狀態**：審查時 `education/REVIEW_STATUS.md` 原本即為未追蹤檔；本報告沒有修改任何 HTML／CSS／JS。

## 結論

**目前不建議把整套教材標示為「內容正確性已驗收／可發布」。** 免責聲明雖然很多，但免責聲明不能修復錯誤公式、過時法規、捏造或無方法說明的統計、以及把市場敘事寫成確定因果的問題。

應先處理下列發布阻斷項目：

1. 2026 年已變更、且仍處於券商分階段導入期的 PDT／日內保證金規則仍被全站寫成固定的「4 次／5 日／US$25,000」。
2. `tw_reality.html` 暗示透過台灣複委託持有美國公司股票可避開美國遺產稅，這與 IRS 的資產所在地判定不符。
3. `supertrend_guide.html` 的 SuperTrend 翻轉公式漏掉遞迴 final bands／前一根 band，照頁面公式實作會得到不同甚至幾乎不會翻轉的指標。
4. `risk_management.html` 的連虧機率表互相矛盾；Kelly、Beta、避險與清算距離也有實質錯誤。
5. `backtesting.html` 把 Profit Factor 翻成「盈虧比」、誤定義 Sortino，並把模擬分位數誤稱為 95% 信賴區間。
6. `liquidity_grid.html` 把「流動性」定義成停損集中地，並把無法從 K 線證明的「主力故意獵殺」寫成事實。
7. `futures_analytics.html` 從 OI＋價格直接推斷新多／新空，忽略每張衍生品同時有多空兩方；Funding、清算熱圖也被寫得過度確定。
8. `options_volatility.html` 對 Max Pain、GEX、期權大單方向、Expected Move、Covered Call 與 Calendar Spread 有多項錯誤。
9. `trading_psychology.html` 使用未驗證的「90%／80%／3%／6 個月」統計與極不合理的「頂尖交易者長期月報酬 5–10%」；自評表又以未驗證分數做臨床式標籤。
10. `ai_semiconductor.html` 將 FY2024／2025 舊數字混入「2026 現況」，並包含多個無來源或疑似錯誤事件，整頁應拆成「常青方法」與「有日期的市場評論」。

---

## Claude 修訂時必須遵守的共通規則

### 1. 把常青知識與市場快照分開

- 常青教材可以說明定義、公式、限制與分析方法。
- 任何「目前、現在、今年、當前判斷、關鍵價位、政策路徑、公司 Capex、PE、交易所費率、穩定幣市占」都必須附：
  - `資料截至 YYYY-MM-DD`
  - 一手來源 URL
  - 數據口徑（曆年／財年、actual／guidance、價格起訖點、日內／收盤、總報酬／價格報酬）
- 無法建立自動更新與到期提示，就刪除「目前」結論，改成示範資料。

### 2. 不得把未回測的經驗法則寫成統計事實

下列詞句只有在提供資料集、期間、樣本數、標的、頻率、交易成本與可重現計算時才能保留：

- 「70% 機率」「90% 是噪音」「最可靠」「勝率高」「通常 1–2 週後」「歷史上都是」
- 固定價位或固定閾值自動導向買賣動作
- 星級可靠度、任意打分卡、50/30/20 權重、3/5 或 4/6 條件即「有效」

若沒有證據，改成：「這是一個待驗證假設；方向與效力依標的、期間、成本與市場環境而變，使用前需做樣本外測試。」

### 3. 敘述層級要分清楚

每個結論至少標成其中一種：

- **定義／會計恆等式**：可確定。
- **機制假說**：理論上可能，但不能由單一圖形證明。
- **歷史相關**：需列期間與方法，不等於因果。
- **情境示例**：不得偽裝成實際歷史。
- **個人操作規則**：不是普遍真理，也不是「正確答案」。

### 4. 所有測驗必須跟著正文一起改

目前多個測驗把有爭議的敘事設為唯一正解。正文修完後，需全文搜尋同一關鍵字並同步修改：題目、答案索引、解析、速查表、SVG 文字、首頁摘要。

### 5. 台灣用語統一

面向台灣讀者時，正文宜以「選擇權」為主，第一次出現時可註明 options；不要全站混用「期權／選擇權」。`Profit Factor` 應譯為「獲利因子」，「盈虧比」留給平均獲利／平均虧損。

---

# P0：必須先修的具體問題與建議文字

## A. PDT／日內保證金規則已不是全美統一的舊版敘述

**影響檔案與行號**：

- `tw_reality.html:172-199, 326-328, 365-372`
- `trading_strategy.html:161, 165-166, 654, 778`
- `backtesting.html:883`
- `trade_home.html:75, 186`
- `precious_metals.html:369`
- `us_equity_etf.html:73`

**問題**：FINRA 的 SR-FINRA-2025-017 已核准以 intraday margin standards 取代舊 day-trading margin provisions；Rule 4210 頁面列示該修訂於 **2026-06-04 生效**。核准命令也允許會員券商在 18 個月期間分階段導入。因此在 2026-11-07，不能再把舊「5 日 4 次＋US$25,000」寫成所有美國券商一律適用的現行規則。

**建議替換文字**：

> 截至 2026-11-07，FINRA 已以新的日內保證金標準取代舊版 PDT 條文，券商仍可在過渡期內分階段導入，因此不同券商與帳戶目前可能適用不同的日內交易限制、保證金算法與 house rules。下單前請直接查看承作券商當日的 intraday margin／frequent trading 規則。現金帳戶雖不使用融資，仍受 T+1 交割、settled funds、free-riding 與 good-faith violation 等限制。

不要保留舊規則作測驗唯一答案；如要介紹歷史，標成「2026-06-04 前的舊制」。

**來源**：

- [FINRA Rule 4210](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210)
- [SR-FINRA-2025-017](https://www.finra.org/rules-guidance/rule-filings/sr-finra-2025-017)
- [FINRA：Frequent Intraday Trading](https://www.finra.org/investors/investing/investment-products/stocks/day-trading)

## B. 複委託不會因帳戶在台灣就自動避開美國遺產稅

**影響檔案與行號**：`tw_reality.html:79-81, 139-166, 291-303, 341-348, 370-372`

**錯誤核心**：`tw_reality.html:161` 的「透過複委託持有……可避開美國遺產稅的直接適用」會讓讀者做出錯誤資產配置。IRS Form 706-NA instructions 明確說明：**不論股票憑證實際放在哪裡，依美國法設立公司的股票通常是美國所在地資產**。判定重點是發行人／基金 domicile 與資產法律性質，不是券商或保管帳戶所在國。

**另需修正**：

- 「美國掛牌 ETF」改成「美國註冊／domiciled 的基金或信託」；掛牌交易所本身不是充分判準。
- US$60,000 更精確地說是 Form 706-NA 的申報門檻及相關 unified credit 所對應概念，不能簡化成所有人的固定「免稅額」。
- 40% 是最高邊際稅率，不是整筆持倉必然被課 40%；刪除「會影響身後 40%」這種誤導句。
- GLD／SLV 通常不配發一般股息；`291` 的「股利／配息預扣比照美股」不應概括。
- 愛爾蘭 UCITS 的美國股息稅是在基金層級依條約處理，投資人層級仍依基金 share class、居住地與當地法規而異。保留時必須加專業諮詢與基金 domicile 查核。

**建議替換文字**：

> 對非美國公民且非美國居民者，美國遺產稅是否適用，主要取決於資產是否屬 U.S.-situs；美國公司股票通常不因改由台灣複委託保管而改變其 U.S.-situs 性質。券商所在地可能影響繼承作業流程，但不是消除遺產稅的工具。基金則應查其法律註冊地／domicile，而不是只看在哪個交易所掛牌。跨境遺產規劃必須由熟悉美台稅務的專業人士依個案確認。

**來源**：

- [IRS：Estate tax for nonresidents not citizens](https://www.irs.gov/businesses/small-businesses-self-employed/estate-tax-for-nonresidents-not-citizens-of-the-united-states)
- [IRS：Form 706-NA Instructions，Stock situs](https://www.irs.gov/instructions/i706na)
- [SIPC 保護範圍](https://www.sipc.org/for-investors/what-sipc-protects)

## C. SuperTrend 公式漏掉關鍵遞迴步驟

**影響檔案與行號**：`supertrend_guide.html:185-226`，以及所有用 ST(300,3) 當唯一正解的頁面與測驗。

`supertrend_guide.html:186` 只列 basic bands，然後用當根 `Close > Upper Band`／`Close < Lower Band` 翻轉。標準 SuperTrend 還要計算會沿用前值的 final upper/lower bands，並依前一根 SuperTrend 狀態切換。漏掉這一步，結果不是同一個指標。

**建議以平台實作為準，正文改成下列層次**：

```text
basicUpper = hl2 + multiplier × ATR
basicLower = hl2 - multiplier × ATR

finalUpper = basicUpper < prevFinalUpper OR prevClose > prevFinalUpper
             ? basicUpper : prevFinalUpper
finalLower = basicLower > prevFinalLower OR prevClose < prevFinalLower
             ? basicLower : prevFinalLower

若上一根 ST 在 upper band：close > finalUpper 才翻多；否則維持空。
若上一根 ST 在 lower band：close < finalLower 才翻空；否則維持多。
```

不同平台在初始值、ATR 平滑與相等條件可能略有差異，教材要明示以實際平台結果為準。

同頁 `220-226`「翻轉代表從均值跌超過 3×ATR」也不成立，因為 band 是遞迴 trailing band，不是固定均值的三標準差事件，應刪除。

**來源**：[TradingView Supertrend calculation](https://www.tradingview.com/support/solutions/43000634738-supertrend/)

## D. 連虧機率表錯誤且自相矛盾

**影響檔案與行號**：`risk_management.html:481-492, 1289-1295`

頁面同時寫「200 筆中 8 連虧約 45%」與「幾乎必定遇到」，兩者互相矛盾。若假設每筆獨立、勝率固定 50%，計算 200 筆中至少出現一次連虧的機率約為：

| 連虧長度 | 正確機率（200 筆、獨立、p(loss)=0.5） |
|---|---:|
| 5 | 96.59% |
| 8 | 31.97% |
| 10 | 8.99% |
| 12 | 2.30% |

真實交易常有序列相關與 regime clustering，因此不應把這張獨立 Bernoulli 表當保證。請在表頭寫清楚交易筆數、獨立性、固定勝率與演算法；不要再用「1000 次模擬」而不交代每次模擬含幾筆交易。

## E. Kelly、Beta、避險與清算的概念錯誤

**影響檔案與行號**：`risk_management.html:582-645, 676-689, 840, 884-941, 1013-1103, 1146-1256, 1415-1630`；`trading_strategy.html:1389-1417`

必修：

- Half-Kelly「保留 75% 成長率、只有一半波動」只是在理想模型／局部二次近似下的常見說法，不是普遍定律；最大回撤沒有固定 50–70%。
- 超過 `f*` 後 expected log growth 會下降，但不是一超過 `f*` 就必然變成負成長。
- 二元賭局的 Kelly stake 不能直接等同「交易投入資金」或「停損風險」。若損失不是整筆 stake，需使用一般化報酬分布模型。
- Beta 是 `Cov(asset, market) / Var(market)`，衡量市場系統性敏感度，不是總波動或「等效 SPY 風險」。刪除 GLD／SLV／BTC 的固定 Beta 換算與相關測驗。
- Long TLT 不能被稱為「利率風險對沖」；殖利率上升造成的科技股下跌時，TLT 也可能跌。它較可能對沖成長／通縮衝擊，不保證對沖通膨或 term-premium 衝擊。
- Long GLD 並非 GDX long 的對沖，只是加入波動較低、相關不完全相同的同方向黃金曝險。
- Stablecoin 不是現金或無風險資產；「分散到 2–3 種穩定幣」也不能替代對儲備、贖回權、司法管轄、智能合約與交易所風險的審查。
- 通用爆倉公式無法涵蓋逐倉／全倉、線性／反向合約、階梯維持保證金、標記價格、手續費、資金費率與交易所規則。應刪除泛用「精確」計算器，或要求使用者選定交易所與合約後引用該交易所公式。
- 不得把 2x／3x 標成「安全」，也不要向新手推薦 2–3x、資深者 5–10x。

## F. 回測統計定義與計算器

**影響檔案與行號**：`backtesting.html:394-506, 509-546, 715-838, 979-986, 1042-1221, 1269-1306`

必修：

- `Profit Factor = gross profits / abs(gross losses)`，中文用「獲利因子」，不是「盈虧比」。盈虧比通常是平均獲利／平均虧損。
- Sortino 分母不是「只挑負報酬後再算標準差」。常見定義是相對 MAR／target return 的 downside deviation：`sqrt(mean(min(0, r_t - MAR_t)^2))`；需說明採用的版本與年化頻率。
- `std × 0.7` 沒有統計依據。`calculateMetrics()` 在使用者沒填 downside deviation 時應顯示「資料不足，無法計算」，不能產生假數字。
- Sharpe 的報酬、無風險利率與標準差必須同頻率，再一致年化；不能只讓使用者任意輸入「年化報酬」與未標示頻率的 Std。
- 將輸入期望值乘交易數只能得到模型期望，不是「總利潤」。標籤改成「在固定分布假設下的期望總值」。
- Monte Carlo／bootstrap 的第 95 百分位是「在指定重抽樣模型下的模擬分位數」，不是未來最大回撤的 95% 信賴保證。單純洗牌會破壞序列相關；至少說明 block bootstrap／regime bootstrap。
- 「實際連虧超過 95% CI ⇒ 有超過 95% 機率不是正常波動」是錯誤的假設檢定解讀，且持續監控會有 multiple-testing 問題。
- 三個月負 Sharpe 沒有自動「統計顯著」；刪除正文與 Q10 的唯一正解。
- ADX > 25 只是常見啟發式門檻，ADX 不表示方向，也不保證趨勢策略優於均值回歸。
- 回測偽代碼需處理同一根 bar 同時觸及停損與停利時的 intrabar ambiguity、下一根成交、限價單未成交、滑點與公司行動。

## G. 流動性／停損獵殺定義錯誤

**影響檔案與行號**：`liquidity_grid.html:198-485`；`market_psychology.html:439-680, 1261-1391`；`candlestick_patterns.html` 全頁「主力」解讀。

建議把流動性定義改成：

> 市場流動性是以有限價格衝擊快速成交的能力，常以買賣價差、可見與隱藏深度、成交量、價格衝擊及下單後的深度恢復速度衡量。

必修：

- 未觸發的 stop order 通常不是可成交的 limit-book 流動性；觸發後才可能變成市場單或限價單。
- Order book 只顯示特定交易場所的可見掛單，不是「所有未成交單」；還有 hidden／iceberg／off-exchange liquidity。
- K 線影線只能證明該段期間的價格路徑，不能證明某個「主力故意推價獵殺」。
- FVG 是 Smart Money Concepts 的三根 K 線圖形定義，不等於該價格區間「沒有成交量」，也沒有必然回補機制。
- 掛單靠近時取消不等於 spoofing；合法撤單非常普遍。Spoofing 需要可證明下單時即無成交意圖。
- 停損放遠會增加每單位風險；只有同步縮小部位，帳戶風險才不變。不能把「被停損」一概歸因於停損太近。
- 網格不是「不預測方向」，而是下注價格在指定期間內反覆穿越格線且已實現波幅足以覆蓋全部成本。極低波動反而可能完全沒有可配對 fills。
- Limit order 只有在不立即成交、並實際增加 order-book liquidity 時才是 maker；若要保證 maker，需使用交易所支援的 post-only。

## H. OI／Funding／CVD／清算熱圖被過度解讀

**影響檔案與行號**：`futures_analytics.html:152-359, 367-759, 767-1176`；`onchain_crypto.html:1042-1081`；其他頁面的 OI 四象限。

必修：

- 每個未平倉合約同時有一個 long 與 short。OI 上升不能單憑價格方向判定「新多」或「新空」；可能是避險、套利、跨市場 basis trade 或不同主動方。
- OI 金額會隨幣價上升而機械增加，應說明 coin-margined／USD-margined 與 normalized OI。
- Funding 正負的付款方向可確定，但 funding schedule、interest component、cap／floor 隨交易所與合約而異，不是一律每 8 小時固定三次。
- `0.03% × 3 × 365 = 32.85%` 是維持固定 rate 的簡單 APR 情境，不是可實現 APY；還要交代兩腿資本、保證金、借幣、手續費、basis、清算與對手方風險。
- 清算熱圖多為供應商依公開資料與假設估算，無法知道所有帳戶的 entry、leverage、collateral 與 maintenance tier，不能描述成「會被清算的實際金額」。
- 不得把清算區稱為一定會吸引價格的磁鐵，或教讀者在估算區下方掛單抄底。
- Long/Short ratio 的定義依平台不同，可能是全帳戶、top traders accounts 或 positions ratio；不是一律「散戶人數比」。
- `Funding > 0.1% ⇒ 70% 機率 24h 回調` 等百分比與只列五個事件的表不能支持統計結論，應刪除或提供完整可重現樣本。

**來源**：[CFTC COT explanatory notes（OI 的 long 總量等於 short 總量）](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm)

## I. 選擇權頁面的重大錯誤

**影響檔案與行號**：`options_volatility.html:149-338, 347-625, 633-895, 905-1424`

必修：

- Call／Put「到期前可行使」只適用 American-style；European-style 通常只能在到期時行使。
- Black-Scholes 因子表漏掉 dividends／carry。
- Delta 是局部價格敏感度；把它當到期 ITM 機率只是在特定模型／measure 下的粗略近似，不是 assignment 機率或「安全率」。
- `Volume > OI` 不能證明新建倉；成交在 ask／bid 也不能可靠判定整個策略方向，因為可能是 stale quote、多腿單、股票對沖或平倉。
- Dark-pool print 無法只靠公開成交判定「大額買入／賣出」。
- Max Pain 應定義為「依未平倉量估算、使到期 aggregate intrinsic payout 最小的價格」，不是「最多合約歸零」；更不能說 market maker 有意願操縱價格到該點或因此獲利最大。
- GEX 是供應商根據 OI、Greeks 與 dealer-position 假設做的估算，實際 dealer 淨倉不可由公開 OI 直接知道；正／負 GEX 與波動的關係是條件式機制，不是方向或波幅保證。
- `Expected Move = straddle × 0.85` 是交易圈啟發式，不是定義；`S × IV × sqrt(T)` 是模型近似。68% 是常態／lognormal 模型的 one-sigma 性質，不是市場必然實現率。
- 「超過 Expected Move ⇒ straddle 買方獲利」錯誤。到期 break-even 取決於實付總權利金；若 expected move 使用 0.85×straddle，超過它仍可能虧。
- Calendar spread 在財報後不保證獲利；近月 gap、兩腿 IV crush、theta、assignment 與 skew 都會影響。
- Covered call 的 premium 只是小幅 downside cushion，股票下跌仍可大虧；`白賺 $200/周` 必須刪除。若投資人不想股票被 call away，最可靠方式是不賣 call 或提前買回，20–30 delta 並非 70–80%「安全」。
- VIX 低不代表 VIX call 便宜；需看 VIX futures、skew 與 option premium。不得把 VIX <13／>35 直接變成買／賣指令。
- `Short Put + Bull Put Spread` 沒有「向下保護」的日常語意；只是把最大損失限制在 spread width 減 credit。

**來源**：

- [OIC Covered Call](https://www.optionseducation.org/strategies/all-strategies/covered-call-buy-write)
- [OIC Protective Put](https://www.optionseducation.org/strategies/all-strategies/protective-put-married-put)
- [OIC Delta](https://www.optionseducation.org/advancedconcepts/delta)
- [OIC Assignment](https://www.optionseducation.org/referencelibrary/faq/options-assignment)
- [Cboe VIX FAQ](https://www.cboe.com/tradable_products/vix/faqs/)

## J. 心理統計、報酬期望與「心理健康」評分

**影響檔案與行號**：`trading_psychology.html:418-489, 498-529, 967-1037, 1106-1127, 1219-1227, 1553-1714`；`cognitive_traps.html:142-412`

必修：

- 刪除或提供可核對研究的「90% 散戶長期虧損、平均存活 6 個月、80% 因心理、3% 穩定月獲利」。目前來源描述不足，而且四個數字不是同一母體／定義。
- 「技術 20%、心理 80%」是口號，不是統計。
- Prospect Theory 常見的 2.25 是特定 value-function loss-aversion 參數估計，不能寫成神經科學上的「痛苦是快樂 2.25 倍」。
- 「杏仁核接管、前額葉被關掉」「運動把皮質醇與腎上腺素消耗完」「命名情緒就削弱控制」都應改成較保守、可引用的心理教育說法，避免 pop neuroscience。
- `月 5–10% 是頂尖交易者長期水準` 極度誤導：5% 月複利約 79.6% 年化，10% 月複利約 213.8%；2–3% 月複利約 26.8–42.6%。這不是一般散戶的「合理期望」，也不能稱為穩定可持續。整段改成「不設定固定月報酬目標，以稅費後、風險調整後績效相對合適基準評估」。
- 心理自評表不是經驗證量表，不能按任意總分標示「心理健康／嚴重問題」或指定「停兩週、讀某書、連續一個月 90% 才復出」。改成不計分的自我覺察清單；若失控、追損、影響工作家庭，建議停止交易並尋求專業協助。
- 胸悶、呼吸困難、明顯心悸不應只歸因交易心理；應加上「若症狀嚴重、首次出現或持續，尋求醫療評估；緊急時聯絡 119」。
- 4-7-8 呼吸可作自我安定選項，但不應宣稱特定生理療效；不舒服或有呼吸／心血管問題者停止並改自然慢呼吸。

---

# 逐頁審查

## `ai_semiconductor.html` — **整頁重寫，發布阻斷**

主要問題：

- `77-82` 混用不同公司、不同財年與不同版本 guidance；2025 預估到 2026/11 已過期。
- `85` 把資金流畫成 Hyperscaler → NVIDIA → TSMC → ASML 的單一路徑。實際上 NVIDIA 是 fabless、向代工／封裝採購；TSMC 自行向設備商採購，hyperscaler 也直接買網路、電力、建築與自研晶片，不能畫成一筆錢逐層傳下去。
- `104-107` 的光纖 US$500B、利用率 5%、挖礦 US$30B 與回本失敗沒有來源與口徑；AWS 2015 是 Amazon 首次分部揭露，不等於「那年才開始盈利」。
- `114-118` token 降價也可能來自推理效率、競爭與規模經濟，不能直接推出 GPU 單位利潤下降；SoftBank「兩次以 OpenAI 股票質押失敗」需一手來源，否則刪除。
- `139-145` 把 AVGO／Marvell 分在封裝層錯誤；兩者主要是設計／網通／客製晶片供應商。封裝例子應另列 TSMC advanced packaging、ASE、Amkor 等，並分清 interconnect。
- `148` 的崩盤順序沒有歷史定律支持。
- `161-168` OpenAI 的競爭狀況不能代表整個 AI 基礎設施 ROI；同時期 Capex growth 與 AI revenue growth 也因折舊期、多用途資料中心與無單獨披露而不可直接比較。
- `164` Anthropic／Perplexity IPO 與「內部人套現」的敘述無來源；IPO 本身也不能證明估值到頂。
- `185-196`「2000 年公司多數零營收／AI 100% 相同」過度概括；Cisco、Microsoft、Intel、Oracle、Sun 等當時都有大量營收。
- `190-196` NVIDIA US$60B 是 FY2024 附近舊數字，不能放在 2026 比較表。
- `210-219, 232-243, 298-303` 把 2026 季度預測與單日跌幅做成「歷史時間線／泡沫評分」，屬市場評論，不是教材。
- `236` 閾值寫成 `> -30%` 邏輯方向錯；若要表示跌幅至少 30%，應用 `return ≤ -30%` 或「跌幅 ≥30%」。
- `258` coding copilot 2x 需指明研究、任務與測量方法，不能泛化到所有工程工作。
- `287`「可重倉 NVDA/TSMC」、`322-326` 固定 put 成本／pair trade、`331-348`「短線最安全」皆不應作通用建議。

**修訂方向**：保留「如何讀 Capex、供應鏈位置、ROI、集中風險」的常青框架；把所有 2025/2026 公司數字移到獨立、具 as-of/date/source 的市場快照。泡沫分數改成研究清單，不輸出交易指令。

## `backtesting.html` — **重大修正**

除 P0 F 外：

- `266-272`「歷史沒通過，未來幾乎不可能盈利」過度確定。歷史樣本不代表部署環境；應改成「在代表性樣本中無法證明正期望，沒有足夠理由部署」。
- `312`「5+ 個參數幾乎肯定 overfit」是未驗證 heuristic；參數有效自由度與搜尋次數比名目數量更重要。
- `367` 固定保留 30% OOS 不是通則；時間序列需 chronological split／purged CV，比例依樣本量與策略更新頻率而定。
- `398, 414, 482-492` 所有「好／傑出」門檻依頻率、資產、槓桿、流動性與期間不同，只可標成示例。
- `747` Walk-forward 不是「最嚴謹」且不是完全真實 OOS；若反覆看結果改策略仍會洩漏。
- `794-837` 補上 serial correlation、fat tails、parameter uncertainty 與 multiple testing 限制。
- `880` 複委託低消 US$15–40 需逐券商與日期來源；目前不少方案已變動。
- `901` 普通 iid bootstrap 不適合有自相關的交易報酬，建議改 block bootstrap。
- `1192-1199` ADX 題改成「常見但需驗證的趨勢強度 heuristic」，不能問出唯一適用策略。

## `candlestick_patterns.html` — **重大概念重寫**

- `192-193` 的限制聲明方向正確，但正文與速查表大量違反這個聲明。
- 全頁星級「可靠度」沒有資料集、期間、成本與樣本數，全部刪除或改成「教材未提供可泛化勝率」。
- `225, 258, 291, 325, 359, 424, 456, 514, 552, 590, 628...` 不能從 OHLC 推知大型資金在吸籌、出貨、洗盤或「故意」製造高低開。
- `475` 週線不天然比日線更可靠，只是訊號較慢、樣本較少、持有期不同。
- `721-723, 766-811, 1048-1054`「最強／公認最可靠」需可重現研究，否則改成傳統名稱與條件定義。
- `1149, 1198-1203, 1257, 1313-1316, 1367-1371` 的 3–5%、2–4 週、1.5 倍量、38.2%、3 週、5 個觸點是技術分析慣例，不是自然定律。
- `1850-1852` Fibonacci 0.618 不是「最後防線」，跌破也不代表趨勢必然反轉。
- `1907`「價格 95% 時間在 ±2σ 帶內」錯誤。Rolling price bands 不滿足獨立常態抽樣假設，實際 coverage 依市場與參數而變。
- `2026-2207` 任意 3/5、4/6 打分不能稱為有效訊號。

**修訂方向**：把頁面改成「形態語法與條件定義」，每個形態列出 bull/bear/neutral 三種可能解釋及失效案例；不推斷隱藏意圖、不給星級與固定交易答案。

## `capital_flow_commodity.html` — **重大修正**

- `45-56` 金融資產不是四池零和遊戲；資產市值、銀行信用、發行／回購與跨境資產負債都可變。MMF AUM 高不代表股票場外有等額「彈藥」。
- `84-94` MMF AUM 受政策利率、機構現金管理、名目經濟規模與銀行存款替代影響，不是單純恐懼指標，也不能推出未來爆發性流入股票。
- `104-113` 同日股債金價格組合只可作情境假說，不能證明資金從一池流到另一池。
- `123-145` 家庭股票配置不是 Buffett Indicator；「所有人 all-in、沒有新買家」是錯誤市場機制。
- `150-196` AAII、margin debt、CAPE、put/call 的固定泡沫閾值需完整回測；AAII 是意見調查，不代表受訪者已 all-in。
- `230-244` 交易所庫存只是可見／可交割庫存，不是全球總庫存；倉庫轉移與融資交易可大幅改變數字。
- `251` COT 報告時間需分夏令／冬令，且持倉資料截至週二、通常週五發布。
- `255-266` Commercial 是套保分類，不是方向預測；淨空常是生產商正常 hedge。Non-reportable 不是等同散戶，也不能寫成「通常錯」。
- `282-296` Backwardation 可反映 convenience yield／近端稀缺，但不保證現貨上漲；`short near / long far` 是 curve-spread 部位，也不是一般「偏空」的同義詞。
- `299, 317-368, 732-738` 固定 1–2 個月需求真空與關稅實施日見頂是未驗證劇本。
- `381-385` LTHM 已不是可長期沿用的現行 ticker；所有公司／ETF 名單須按 2026-11 狀態重查。智利政策不應簡化成「國有化風險」。

## `cognitive_traps.html` — **重大修正**

- `225-227` loss aversion 倍數與演化故事改成有來源且保守的敘述。
- `261, 278, 301, 365, 379`「連勝後必須減半」「50/30/20 歸因」「到目標永遠走」「逆勢每天只做一次」皆是作者規則，不是心理學結論。
- `311` 金融報酬並非獨立擲硬幣；動能與均值回歸都可能存在，不能說第六天下跌機率與前五天完全無關。
- `379` stop order 可能滑價或無法成交；系統也可能故障。
- `407` 不動可能是理性持有，不應一律「立刻行動」。
- 多個測驗把可爭議的交易管理方式設唯一答案：`473-480, 490-516, 635-661, 689-747, 755-827`。改問偏誤辨識，不問未經驗證的唯一交易動作。
- `635-643`「直覺想清倉就市價平一半」與整頁主張的規則化決策互相矛盾，應刪除。

## `event_trading_sop.html` — **發布阻斷**

- `65-82` 主表只列夏令時間，未標冬令；後面 `306-317` 才有正確雙版本。主表必須合併修正。
- `63-93` Tier 與「單日 2–5%／1–2%」沒有樣本與資產定義。
- `102-105` 財報不是 50/50；價格反應由 surprise distribution 與已隱含波動決定。
- `132-157, 185-247` 25%／50% 減倉、前 5 分鐘 90% 噪音、15–30 分鐘是真方向、第二波較可靠，全是未證實規則。
- `152` 與 `209` 的 90% 數字應直接刪除。
- `187` 15–30 分鐘後不可能同時用「1h ST 收盤確認」，時間尺度互相矛盾。
- `287-293` 所謂一小時「歷史平均波動」沒有期間、起訖定義與來源，而且絕對美元值會隨資產價格失效。XAU ±US$80–150、XAG ±US$2–4、SPX ±1.5–3% 作為平均值高度可疑。
- `293`「US$1 stop 100% 被打到」錯誤。平均絕對波動不等於每條路徑必定穿越某 stop。
- `43, 293` 不應教讀者為了過事件而單純放寬 stop；gap risk 無法由 stop distance 封頂。優先說明減少名目曝險、退出或使用明確成本的 hedge。
- 刪除個人化但無上下文的「你的白銀爆倉」「$65→$61.53」。

## `forex_analysis.html` — **發布阻斷**

- `184-197` direct／indirect quotation 的名稱依本國貨幣視角而變，建議只教 base／quote currency，避免用「以美元為基礎」當定義。
- `203-242` 固定五大驅動排序與「高息貨幣必升」過度簡化；未拋補利率平價顯示高利率常伴隨預期貶值／風險溢價。
- `231-237` QE 不必然使貨幣貶值、QT 不必然使貨幣升值；貿易順差也不會機械導致升值。
- `285-289` REER 公式需先定義匯率方向與權重；極低 REER 不保證均值回歸或「商品全球極便宜」。
- `377-400` DXY 是六幣相對價格指數，不是美元流動性存量。海外美元債成本還取決於借款人本幣、期限與 hedge。
- `438-500` DXY 7–10 年固定週期、95／100／103／115 等交易門檻、年度 ±10% 的全球牛熊規律全部刪除。
- `490-498` 2022 黃金全年不是簡單 `-20%`；這看似把 peak-to-trough drawdown 當全年報酬。所有歷史表需統一起訖點。
- `534-537` 2024/3 BOJ 已結束負利率與 YCC；2024/7 是升息及減少 JGB 購買計畫，不是「調整 YCC」。
- `539-595` US$3–5T carry 規模與分項無可靠官方統計；日本壽險海外資產不能全部當成短 JPY carry 加總。
- `601-620` 145／140 等固定危機水位及單日跌 1.5／2.5% 自動防禦是事後擬合；USD/JPY 下跌也可能來自美債殖利率下降，未必利空股票。
- `637-640` 2022/9/22 干預發生在約 145–146，不是先到 150；150 附近是 10 月後續干預。
- `684-802` TWD 與台股／外資流雙向影響，不能把台幣升值當外資買股的唯一確認。CBC 尾盤操作與「只能改速度不能改方向」需要來源與更中性文字。
- `742-775` CNH 不是完全自由市場；7.35、TWD 33.5、KRW 1450 等固定「危機」線會過期，移除。
- `826-950` EUR 1.10、AUD 0.68／0.63、EM 貨幣價位等不能直接確認全球 regime。
- `980` 將 0.5–1% 日波幅乘 365 得出 180–365% 年化波動是數學錯誤。若 0.5–1% 是日標準差，常見年化方式是乘 `sqrt(252)`，約 7.9–15.9%，仍需確認資料定義。
- `1047-1053` FX session 沒有官方股票式開盤，且台灣時間會受歐美各自 DST 與切換週差異影響。
- `1248-1259` 股票、債券、FX、黃金等電子市場會近乎同時反應，不能宣稱看 FX 可在 5–20 天前布局股票。
- `1270-1315` 危機固定 5–7 日完成、2–4 週恢復是捏造式時間表。

**來源**：[BIS 2022 Triennial Survey：FX 日周轉 US$7.5T，且口徑包含 swaps 等](https://www.bis.org/statistics/rpfx22_fx.htm)

## `futures_analytics.html` — **發布阻斷**

除 P0 H 外：

- `162` OI 不是槓桿量；可能有 fully collateralized／hedged positions。
- `194-260` 四象限全部改成「可能解釋」，不得寫「真漲／健康趨勢／接近底部」。
- `308` 100x 實務上可能在未到 1% 前因 maintenance margin／fees 被清算。
- `309-310` 清算不一定單純以市價單執行；各所可能 partial liquidation、insurance fund、ADL。刪除「清算引擎是最大鯨魚」。
- `350-359` Binance 40–50%、Binance=散戶、Bybit=專業等分類無來源且會變。
- `563-565` positive funding 的付款方向正確，但不能必然等同 perp 當下高於 spot。
- `704` 兩腿放同一交易所降低轉帳風險，卻增加共同交易所倒閉／凍結風險；必須呈現 trade-off。
- `912`「傳統市場最高 5–10x」錯誤，期貨與選擇權可有更高有效槓桿。

## `liquidity_grid.html` — **發布阻斷**

除 P0 G 外：

- `238` 前低範例把空單停損位置寫錯；前低下方常見的是多單 sell stop，上方前高才常見空單 buy stop。
- `255, 271, 279` 第三次必破、最終被吸引、盤整七天後劇烈等無證據。
- `287` book 不是所有訂單，`304` stop 也可被取消或修改。
- `312` 100,000 BTC 範例與「做市商要買」混淆 market maker 與 large asset manager／directional trader。
- `392-465` SMC／FVG 應明示為流行技術分析框架，尚無普遍接受的因果驗證。
- `498-607` 網格需要「足夠來回波動」而非單純低波動；重大事件不是唯一 breakout 來源。
- `632-640` 每一次 fill 不會自動產生已實現利潤，需有相對應的反向成交；中性網格也通常需初始 inventory／margin。
- `695-698, 916-920` 15–30 grids、20%／40% 配置、5% kill switch 不是通用鐵律。
- `775-781` 交易所費率高度時效化；必須逐交易所官方頁附 as-of date。Maker 0% 仍有 adverse selection、spread、funding、稅與基差成本，不能稱「純利潤」。

## `macro_liquidity.html` — **發布阻斷**

- `161-171, 247-281` `Fed assets - TGA - ON RRP` 是市場常用 proxy，不是官方「全球淨流動性」定義。相關係數若用非平穩 level series 容易產生 spurious correlation；0.70／0.75／0.85 必須提供資料、轉換、lag 與程式。
- `256, 328, 351` RRP 減少不等於同額資金流入風險資產；ON RRP 是 Fed 負債組成從 RRP 到 reserves 的轉換，還取決於 T-bill 買方與結算路徑。
- `292` BTFP 本身峰值並非 US$300B+；不要把更廣泛 discount-window lending 混成 BTFP。
- `293` Fed 在二級市場依貨幣政策授權操作，不應寫成「配合財政部融資需求」。
- `318` MMF 不能拿 IORB，應比較 ON RRP offering rate、T-bill、repo 與其他可投資工具。
- `328, 516-530` 2023 TGA 先在債限期間下降、解決後又重建；不能把不同期間端點加總成簡單 US$1.1T 並歸因股市上漲。
- `397-441` QE 創造 reserves，不宜寫成一般語意的「印錢後銀行拿去買股票」。Portfolio balance 是可能傳導，不是每一美元被迫追股。
- `453-464` 2019 repo shock 成因包含公司稅、Treasury settlement、dealer balance sheet 與 reserves 分布，不是單因 QT 過頭。
- `501-504` Dot plot 是個別 FOMC participants 在各自適當政策假設下的 projection，不是 Committee 承諾或「官方指引」。
- `540-553` FOMC 反轉 50%、第 2–5 日更可靠無來源。
- `615-659` 2s10s／3m10y 必須分開。衰退預測紀錄、倒掛次數與 lead time 取決於 spread 定義；un-inversion 可由短端跌或長端升，不等於 Fed 已判定衰退，更不是自動做空點。
- `696-701` 利率升銀行股未必受益，還看曲線、deposit beta、duration loss 與 credit；殖利率下降也可能代表衰退衝擊、股票同跌。
- `711-764` DXY 不是 master variable；固定 -0.6 至 -0.8 相關無方法。
- `777` GBP 不「跟隨 ECB」，主要受 UK／BOE 與相對基本面影響。
- `1065` 低 HY spread 可長期維持，不是必然暴風雨前兆。
- `1081-1092` MOVE 領先 VIX 1–2 週與 MOVE>120/VIX<20 買 VIX call 的規則無證據，且「最終一定傳導」錯誤。
- `1109-1111` BTFP 已在 2024-03-11 停止新貸款，2026 年不能列為現行即時壓力工具。
- `1174-1213` FRA-OIS／TED 依賴已退出主流的 LIBOR 架構；改用 SOFR、repo、CP/OIS、cross-currency basis 等現行指標，並移除固定 lead times。
- `1229` Fed 的 2% longer-run goal 指 headline PCE，Core PCE 是重要訊號但不是目標本身。
- `1266-1278` 40% 假動作、NFP 平均下修 5–8 萬需重做資料；修正值重要，但當期 surprise 也不能忽略。
- `1305` V/U>1.5 不代表 Fed「不會降息」。
- `1361-1376` 「supercore」不是法定目標，且 2024–25 趨勢到 2026 已過時。
- `1387-1433` Household Equity Allocation 不是 Buffett Indicator。歷史表混用三年報酬、一年 drawdown 與 peak-to-trough drawdown；0–3% 等未來年化區間沒有回歸模型，全部重算或刪除。

**來源**：

- [NY Fed ON RRP FAQ](https://www.newyorkfed.org/markets/rrp_faq)
- [Fed Open Market Operations](https://www.federalreserve.gov/monetarypolicy/bst_openmarketops.htm)
- [Fed BTFP：2024-03-11 停止新貸款](https://www.federalreserve.gov/monetarypolicy/bank-term-funding-program.htm)
- [Fed SEP：個別 participants 的 projections](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20250319.htm)

## `market_psychology.html` — **發布阻斷**

- 全檔有 **85 個 `ï¼` mojibake**，先統一改回全形冒號 `：`。
- `244-324` Wyckoff 四階段是分析框架，不是市場永遠依序運行的可觀察事實，也不能直接知道 smart money／retail 正在做什麼。
- `330-388` 情緒門檻與「三指標即高機率」需回測；Google Trends 歸零／爆量不是普遍頂底。
- `403-404` 80/20 規律無來源。
- `439-655` 刪除「機構製造恐慌／放消息／收割散戶」的因果斷言；即使有市場操縱個案，也不能從價格圖形反推。
- `573-599` CVD、Whale Alert、COT、dark-pool 的方向解讀皆過度確定。
- `661-680` 機構也做超短線、散戶也可長期持有；時間框架不是機構／散戶二分法。HFT 的微秒優勢只代表不能競爭 latency-arbitrage，不代表所有 1 分鐘策略數學上不可能盈利。
- `688-922` 「川普固定先威脅再軟化」「常在 48–72 小時」「週五晚公布是為讓市場冷靜」涉及意圖推斷與樣本選擇。建議整章移出常青教材，改成有事件樣本、來源與 coding rule 的政治事件研究個案。
- `856` 總統免職 Fed 主席的法律問題仍有爭議，不能絕對寫「無權」；同檔 `1907` 的較保守版本更合適。
- `865, 1128` 台灣使用 Polymarket 的合法性不能只寫「灰色地帶」；要引用主管機關／法律意見，否則僅說「使用前自行確認所在地法律與平台條款」。
- `963-1058` 新聞可含真正的新資訊，不是一律落後。BTC ETF、ETH Merge、Fed cut 案例要統一起訖點與控制其他宏觀因素。
- `991-994, 1482-1489`「BTC ETF 核准當天 -5%」需按 SEC 核准時刻與時區重算；目前寫法很可能混入隔日／數日回落。
- `1132-1217` 預測市場事件機率高，不代表該事件對某資產的價格影響已完整 price in；機率、影響幅度與 conditional return 是三個不同量。
- `1171`「降息 80% 但債券沒漲 ⇒ 債券低估」錯誤，債券可能已因期限溢價、通膨與未來路徑不漲。
- `1267-1293` market maker 看不到跨所有場域的完整 order book；GEX 估計限制需補上。
- `1312-1327` 高量＋OI 不變不能識別 wash trading；front running 需定義為利用客戶未公開訂單資訊搶先交易，不能泛化成看到公開大單。
- `1348-1665` 美國監管可對加密商品 spoofing／fraud 執法，不能說「不會被處罰」。
- 大量 quiz 將上述爭議敘事設唯一答案，特別是 Q5、Q6、Q8–18、Q24–27、Q43 等，需全面重寫。

## `onchain_crypto.html` — **發布阻斷**

- `115-166` 原始鏈上資料可近即時，不是必然延遲 1–24 小時；延遲常來自 vendor tier／標籤處理。交易所內部、ETF、L2 與 custodial activity 不在 L1 全貌中，不能說涵蓋所有參與者。
- UTXO 可以追蹤 outputs，不等同精確追蹤每一枚幣的真實成本；合併、拆分、change 與 entity heuristics 都會影響。
- `250-327` NUPL/MVRV 是 realized-cap 模型的 aggregate 指標。MVRV<1 不表示「所有人平均虧損」，MVRV 3.5 也不表示每個人獲利 250%。
- `319-320` Z-score 7／0.1 的買賣規則是歷史 band，不是永久門檻。
- `341-343` 155 天是 UTXO age cohort heuristic，不是「地址持有天數」。
- `354-366` STH realized price 不是可靠保證支撐，LTH supply 下降也可能受 coin aging／entity adjustments 影響。
- `416-425` aSOPR 排除短於一小時 outputs，不足以排除所有 change outputs 或交易所內部搬移。
- `445-460` exchange inflow 只表示流向已標記地址，不等於準備出售；提款也不必然長抱。
- `475-481` halving 只有少數歷史樣本；halving 降低新增發行，不是減少既有 supply，需求也不會自動增加。
- `500-520` staking 上升不一定鎖死流動供給，因 liquid staking／restaking；ETH 日發行量不是固定 1,600。
- `509-510` 5／10／50 gwei 門檻已受 L2 與 EIP-4844 後結構變化影響，不能直接判斷生態健康。
- `558-560` BTC 不是 ETH 下跌時的無風險避險資產。
- `572-581` TVL 可重複計算、受槓桿／restaking／token price 影響；改用 ETH 計價也不是「真實流量」，需看 token units 與 net deposits。
- `660-765` stablecoin mint 可是 treasury inventory／chain swap／authorized-not-issued，不一定有新法幣；USDC 不等於機構 smart money，USDT 不等於亞洲散戶。
- Stablecoin dominance 上升可能只是 crypto denominator 下跌，不能稱 dry powder。
- `780-846` 固定 depeg／yield／市占門檻會過期；DeFi yield 與 Treasury 必須調整信用、流動性、smart-contract、custody 與 duration risk。
- `861-929, 1018-1022` 打分卡任意加總高度相關、重複受價格驅動的指標，卻輸出 70%+ 倉位，應整段刪除或改成不含部位建議的研究 worksheet。
- `1107` GBTC 在 ETF 轉換後不應沿用舊 closed-end trust discount/premium 解讀。
- 測驗 Q2、Q3、Q6–Q8、Q10–Q14 把不確定推論設為唯一答案，需重寫。

**來源**：

- [Ethereum gas 定義](https://ethereum.org/en/developers/docs/gas/)
- [Ethereum L2／rollup 與 blob scaling](https://ethereum.org/en/roadmap/scaling/)

## `options_volatility.html` — **發布阻斷**

見 P0 I。另：

- `131`「多數 long options 到期歸零」需 OCC 統計及母體定義；未持有到期的合約不能算同一件事。
- `358` Block >US$1M 是 vendor threshold，不是市場定義。
- `366` premium 與 stock notional／delta-equivalent notional 混淆。
- `615-625` term structure 倒掛只表示近端 implied vol 較高，不等同近月被高估。
- `677-689` Charm／Vanna hedge flow 的買賣方向取決於 call/put、dealer sign、moneyness 與 position，不能固定成賣壓。
- `716-738` IV>後來 RV 需要相同 horizon／strike 與方差口徑；風險溢酬為正不表示 short vol 是免費優勢。
- `784-788` IV crush 百分比沒有定義是 vol points 或相對百分比。
- `840-850` VIX 長期平均依起訖期間不同；不可用固定水位直接交易。
- `1107-1110, 1160-1165, 1211-1214` spread 寬度、delta、止盈停損、Greeks 上限都是示例規則，不能稱最佳。
- Q8「不想被 call away」的真正答案應是不要賣 covered call，或承認只能買回降低風險且無保證。

## `precious_metals.html` — **可保留架構，但需修正**

- `138` 只有直接持有、妥善保管且無借貸關係的實體黃金才接近「無交易對手風險」；ETF、銀行存摺、期貨與託管金都有 issuer／custodian／broker／operational risk。
- `171-183` 將 2022–2024 歸因央行購金／去美元化可以列為可能解釋，不應說已證明唯一原因。
- `212` 工業需求約一半需附 Silver Institute 年份；比例每年變動。
- `236-255` 央行不是絕對 price-insensitive，也不能保證價格地板；ETF holdings 多是 share creation/redemption 的結果，不一定領先或直接代表情緒。
- `296-301` AISC 不包含所有公司層級成本、成長資本、融資與稅；gold price - AISC 只是粗略 mine margin，不是淨利。
- `361-362` contango 的 roll yield 需連同 collateral yield、期限與 futures convergence 解釋；不能說期貨永遠不是長期工具。
- `375-398` 未提供 seasonality backtest，就不要建議在「偏弱月份」加碼 DCA。
- `409-441` 5–15% 黃金配置是示例，不是所有台灣上班族的通則；要看期限、負債、收入、幣別與風險承受度。

## `regime_identification.html` — **發布阻斷**

- 把 growth、inflation、liquidity shock 與「去美元化」混成同一層級 taxonomy；後者是長期敘事，不是可由單週價格唯一識別的 regime。
- `257-357` VIX、HY OAS、金銀比等固定界線不是普遍分類器；金銀比 >85 也可出現在 deflation／liquidity crisis，並非 stagflation 專屬。
- `368-392` RRP 不是一般散戶可買資產；流動性危機也不是所有 Treasury 一律跌。2023 SVB 期間美債大漲，不符合頁面自己的定義。
- `399-421` BTC／ETH 不是官方儲備替代物；DXY 弱、gold/BTC 漲不能證明去美元化。
- `433-629` 四個市場價格不能在 60 秒內唯一識別宏觀狀態；所有輸出改成「候選解釋＋還需檢查的資料」。
- `648-749` 80–100% 週期股、60–80% 黃金＋加密＋商品、20–30% 黃金、10–15% BTC 是高風險資產配置建議，應刪除。
- `688-724` OTM calls 在危機末期通常 IV 高、到期風險大，不能稱「有限風險無限收益」後就推薦抄底；最大損失雖有限，期望值可能很差。
- `802-851` 所有液態市場會同時定價；「信用領先 1–3 天、FX 2–5 天、股票 5–20 天且散戶為主」錯誤。
- `883` 黃金轉跌不是流動性危機的必要充分條件。
- `892-898, 969-981` 2020 VIX 收盤峰值 82.69 出現在 3/16，不是 3/23；Fed 行動恰逢底部一次，不能當普遍結束信號。
- `915-964` 到 2026/11，將 2025 寫成「假設」已不合時序；整張時間軸需重做或刪除。
- 測驗應允許「資訊不足／多重解釋」，不能用單日四個價格強迫唯一 regime。

## `risk_management.html` — **發布阻斷**

除 P0 D／E：

- `298` 只有勝率與 risk fraction，不能判定 A 必破產、B 必盈利；還需要 payoff distribution、成本、相關性與 edge stability。
- `303-311` 已承認 Risk of Ruin 公式不嚴謹，就不該再畫精確曲線。刪除或限定到有清楚假設的二元等賠率模型。
- `382` fixed-fractional 連虧 10 次不是精確 10–20%；1% 約 -9.56%，2% 約 -18.29%。可寫近似並說明複利。
- `394-400`「專業交易員都冒 0.5–2%」無統一業界標準。
- `590-645` Kelly 問題見 P0 E。
- `695-725` 分清 stop-market 與 stop-limit；前者可能滑價，後者可能完全不成交。用 2–3 倍 stop distance 也無法保證 gap 只虧 1R。
- `840` equity curve 20MA 可降低 drawdown 需回測；也可能 whipsaw、延遲恢復，不能說會大幅降低。
- `884` 標題「槓桿只改變保證金」不完整。若 notional 固定，它主要改變 collateral／清算距離；若 margin 固定，槓桿會直接放大 notional 與損益。
- `896` 0.167 BTC × US$60,000 = US$10,020，不是剛好 US$10,000；改 0.1667。
- `964-1000` 跨交易所 30–40%、stablecoin 20–30% 是任意比例，且 stablecoin 不是現金。
- `1017-1032` 固定相關係數沒有期間與頻率。危機相關性也不必然趨近 1；gold／Treasury 可在不同 shock 下有不同反應。
- `1068-1075` TLT 對沖敘述見 P0 E。
- `1082-1103` Beta 章重寫成 systematic beta 與 total volatility／correlation 的區別。
- 位置計算器要拒絕方向錯誤的 stop、負值／零值，並在 position value > cash 時提示需槓桿；「最大虧損」改成「若 stop 按該價成交的計畫虧損」。

## `supertrend_guide.html` — **發布阻斷**

除 P0 C：

- `202` RMA 比 EMA 慢可說，但「比 SMA 更平滑」需定義；不要把平滑等同更準。
- `214, 249-253` ST(300,3) 的可靠度、每年 2–4 flips、動態支撐與首次回踩最佳均無回測。
- `269-372` 50/30/20 權重與 80–100% 多空部位是任意且危險；不同時框高度重疊，不是三個獨立證據。
- `420-480` 0.3%、1%、2–4 bars、每月四次等真假翻轉規則無資料。
- `431` 事件後 4–6 小時才是真方向無證據。
- `552-567` 固定 5 股 NVDA 不符合風險按帳戶與 stop distance 計算；又說小倉可不設 stop，與全站鐵律矛盾。
- `603-612` 事件前收窄 stop 只會提高被正常波動觸發機率，且無法保護 gap。
- `629-693` 高時框永遠優先與精確 3%／5 天等條件只可作待回測規則。

## `trading_psychology.html` — **發布阻斷**

除 P0 J：

- `524, 611, 689, 997` 改掉單一腦區「接管」與神經傳導物質因果斷言。
- `529-598` 散戶不是完美反指標，smart money 也會錯。
- `621-699, 771-780` 15／30 分鐘、3–5 筆、2%／3% 都是示例 guardrails，不是心理學正確答案。
- `922-927` 賭場類比要補「edge 必須真實、穩定、成本後為正，且樣本不獨立時大數法則收斂更慢」。100 筆不能保證顯現。
- `1111-1127, 1222-1227` 固定月報酬目標整段刪除。
- `1271`「每個場景只有一個正確答案」不適合真實風控；改成「在已明示策略規則與假設下的較合適答案」。
- `1494-1495, 1540-1541`「大賺後 30 分鐘不夠」「下次同樣做 90% 虧」無證據。
- 自評表處理見 P0 J。

## `trading_strategy.html` — **重大修正**

- PDT 全面更新，見 P0 A。
- `355-391, 970-1134` 週一小波動／gap 回補、週二三主攻、週五回歸 Max Pain 是市場 folklore，沒有跨期間證據。建議刪除「五日固有週期」與 30/100/70/30% 倉位圖。
- `470-475` VIX 固定 bands 與 DXY／yield／VIX 三燈號只可作情境，不是買賣結論。
- `502` `current price ± daily ATR` 不是有指定覆蓋率的預測區間，改稱「波動尺度參考」。
- `505` Bollinger squeeze 不保證大行情即將發生。
- `522-530` Funding 閾值與「大清算通常反彈」無證據。
- `670-671` ORB 是**開盤後**前 15–30 分鐘形成的區間，不是「開盤前」。
- `739-777` VWAP 是成交量加權交易基準，不是資產的內在「公平價」；回踩 VWAP 也不是最安全進場。
- `812` 漲 5% 後通常太晚是任意門檻。
- `865-887` 事件風險不是無限，第一根也不一定 stop hunt。
- `1114-1123` NFP 通常但不保證第一個週五；Max Pain 回歸指令刪除。
- `1187-1235` 現貨／槓桿 position formula 需加入合約乘數、FX conversion、fees、gap 與最大可買資金限制。
- `1392-1417` 槓桿安全表與推薦上限刪除；10x＋10% move 只會抹掉該部位 initial margin，不一定是整個帳戶，且通常在 10% 前已因 maintenance margin 清算。
- `1432-1463` R:R 本身不決定 edge；break-even 表忽略成本與未達目標／滑價。改成「在平均 realized payoff 確實等於表中數值時的成本前 break-even」。
- `1501` 12×US$548=US$6,576，不是 US$6,570，可修小誤差。
- `1708`「需要自責」改成「需要檢討流程」，避免把紀律問題人格化。

## `tw_reality.html` — **發布阻斷**

除 P0 A／B：

- `67` 海外帳戶不應一律稱「資產都在美國」；法律實體、custodian 與 account location 依券商安排。
- `79` SIPC 正確說法是總上限 US$500,000，其中現金上限 US$250,000，僅對 SIPC member broker-dealer 的 missing customer property；不是資產價格、投資建議、期貨、FX 或多數 crypto 保險。
- `114-116` NRA 股息一般 30% FDAP withholding，但應註明特殊產品、ECI、qualified interest、REIT／PTP 等例外。資本利得「一般不課」也要補 183-day、ECI、FIRPTA 等例外。
- `149-150` 用「美國註冊／domiciled」取代「美國掛牌」。
- `192` 現金帳戶不只等 T+1；還有 settled funds、free-riding、good-faith violations。
- `208-226` 時區表大致正確，但所有事件仍應連官方 calendar，假日或特殊發布可能改期。
- `249` 分批換匯降低單點時機風險，但不必然「勝過」一次換匯；若資金已備妥，分批也延長未投資與匯率曝險。
- `291` GLD／SLV 是美國商品信託，不宜簡化為一般公司股票型 ETF；稅務與配息另查 prospectus。

**來源**：

- [IRS FDAP 與 NRA capital-gain 例外](https://www.irs.gov/individuals/international-taxpayers/fixed-determinable-annual-periodical-fdap-income)
- [SIPC](https://www.sipc.org/for-investors/what-sipc-protects)

## `us_equity_etf.html` — **可保留架構，但需修正**

- `89-126` 寬基 ETF 有歷史正 equity premium，不是把正期望「鎖住」。需加估值、國家集中、幣別、費用與稅後風險。
- `100-101, 154-156` QQQ 是 Nasdaq-100、排除金融且科技權重高，不等同純科技；IWM 未必有更高長期報酬，small-cap premium 依期間與品質而變；DIA 的防禦性也不保證。
- `120-123` 指數換股不是免費「汰弱留強」優勢，會有 turnover、implementation cost 與先漲後納入效應。
- `113, 204-218` 80%／60-15-15-10 只能保留為明確假想案例，不可暗示適合所有新手；QQQ 與 VOO／VTI 高度重疊。
- `226` 再平衡控制風險，但不保證提高報酬或每次低買高賣。
- `289` 除息日理論價格會受股息影響，但實際市場價格不必精確扣同額。
- `294-336` 分清「未來收入逐期投入」與「手上已有 lump sum 卻刻意分批」。後者通常是在降低短期 regret／timing risk，代價是延後市場曝險，不能一律稱最佳。
- `331-333` 下跌對仍有穩定收入且長期累積者可能有利，但對退休提款者有 sequence-of-returns risk。
- `364-369` GTC 可能有券商最長有效期、corporate action 取消、盤前盤後限制；OCO／stop 不保證成交價。

## `precious_metals.html`、`us_equity_etf.html` 的共同補充

兩頁的 5–15%、1–2%、80% 等比例都應加一句：「這些是示範，不是由資產名稱本身推導出的適合比例；實際配置需依總資產、負債、收入穩定度、期限、幣別與最大可承受回撤決定。」

## `trade_home.html`／`index.html`／`REVIEW_STATUS.md`

- `index.html` 僅導向，未發現內容性問題。
- `trade_home.html:75,186` 更新 PDT 文案；各卡片若保留「穩定副業」措辭，改成「教育與風險管理」，避免暗示交易可穩定產生副業收入。
- `REVIEW_STATUS.md` 說有 24 HTML，但目前實際為 23；同時上方寫「全流程完成」，底部又寫「Round 1 啟動／剩餘未做」，狀態自相矛盾。這個檔案不能再作內容已正確的驗收證據。
- `common.css`／`common.js`／`site.js` 只做了與內容呈現相關的抽查，未做視覺、無障礙或資安審查。

---

# 建議的修訂順序

1. **先修法律／稅務**：PDT、複委託遺產稅、NRA 稅務、SIPC。
2. **再修公式**：SuperTrend、連虧、Kelly、Beta、Sortino、Monte Carlo、Expected Move、清算。
3. **移除假統計**：所有 60/70/80/90%、星級、固定 lead time、固定「最佳」門檻。
4. **重寫市場微結構**：流動性、OI、CVD、Funding、GEX、Max Pain、dark pool、COT。
5. **拆出時效內容**：AI、央行政策、DXY 水位、公司 Capex、交易所費率、stablecoin 市占。
6. **修心理健康內容**：移除虛假績效期望與未驗證臨床式計分。
7. **同步所有 quiz／SVG／速查表／首頁摘要**。
8. **最後才做文字潤飾與版面**。不要先美化錯誤內容。

# 修完後的驗收清單

- [ ] 全站搜尋 `PDT|25,000|2.5 萬`，所有結果均反映 2026 過渡期或標為歷史舊制。
- [ ] 全站搜尋 `穩賺|一定|必然|最可靠|90%|70% 機率|100% 會|唯一安全`，每一處都有定義／來源或已改為條件式文字。
- [ ] 全站搜尋 `目前|當前|2024|2025|2026`，每一項時效數字都有 as-of、來源、口徑與到期處理。
- [ ] SuperTrend 以同一 OHLC fixture 跟 TradingView／選定平台輸出逐 bar 比對。
- [ ] 連虧機率有固定 seed 的模擬測試，並與 exact dynamic-programming 結果比對。
- [ ] Sharpe／Sortino／Profit Factor 對已知 fixture 做單元測試；禁止 `std × 0.7` 假估算。
- [ ] 清算計算器若保留，至少有 exchange、contract type、margin mode、maintenance tier 與 fees 的測試案例；否則移除。
- [ ] Quiz 不再把機制假說或作者偏好當普遍唯一正解。
- [ ] 所有歷史報酬統一起訖、時區、price／total return、close／intraday drawdown。
- [ ] 政策、稅務與交易所規則至少各由一個官方一手來源複核。
- [ ] 對醫療／成癮內容由具資格的心理或醫療專業人士複核；不再稱自製分數為「心理健康」診斷。
- [ ] `market_psychology.html` 的 85 個 `ï¼` 全部修復。
- [ ] 更新 `REVIEW_STATUS.md` 的頁數與狀態，並列出本輪 factual audit 的實際驗收證據。

# 主要一手來源清單

1. [FINRA Rule 4210](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210)
2. [FINRA SR-FINRA-2025-017](https://www.finra.org/rules-guidance/rule-filings/sr-finra-2025-017)
3. [FINRA Frequent Intraday Trading](https://www.finra.org/investors/investing/investment-products/stocks/day-trading)
4. [IRS Estate Tax for Nonresidents](https://www.irs.gov/businesses/small-businesses-self-employed/estate-tax-for-nonresidents-not-citizens-of-the-united-states)
5. [IRS Form 706-NA Instructions](https://www.irs.gov/instructions/i706na)
6. [IRS FDAP／NRA capital gains](https://www.irs.gov/individuals/international-taxpayers/fixed-determinable-annual-periodical-fdap-income)
7. [SIPC：What SIPC Protects](https://www.sipc.org/for-investors/what-sipc-protects)
8. [Investor.gov：Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)
9. [TradingView：Supertrend calculation](https://www.tradingview.com/support/solutions/43000634738-supertrend/)
10. [CFTC：COT Explanatory Notes](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm)
11. [BIS：2022 OTC FX Turnover](https://www.bis.org/statistics/rpfx22_fx.htm)
12. [NY Fed：ON RRP FAQ](https://www.newyorkfed.org/markets/rrp_faq)
13. [Federal Reserve：BTFP](https://www.federalreserve.gov/monetarypolicy/bank-term-funding-program.htm)
14. [Federal Reserve：Summary of Economic Projections](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20250319.htm)
15. [OIC：Covered Call](https://www.optionseducation.org/strategies/all-strategies/covered-call-buy-write)
16. [OIC：Protective Put](https://www.optionseducation.org/strategies/all-strategies/protective-put-married-put)
17. [OIC：Delta](https://www.optionseducation.org/advancedconcepts/delta)
18. [OIC：Assignment](https://www.optionseducation.org/referencelibrary/faq/options-assignment)
19. [Cboe：VIX FAQ](https://www.cboe.com/tradable_products/vix/faqs/)
20. [Ethereum.org：Gas and fees](https://ethereum.org/en/developers/docs/gas/)
21. [Ethereum.org：Scaling／L2](https://ethereum.org/en/roadmap/scaling/)
