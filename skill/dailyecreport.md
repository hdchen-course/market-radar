# 終極宏觀流動性、AI 資本支出與量化籌碼雷達 V4.5

## ⚠️ 強制執行流程（違反任何一步 = 報告無效）

```
STEP 1: TZ='Asia/Taipei' date → 確認台灣時間週幾幾點
STEP 2: 讀上一份報告（from reports.json 最後一筆）→ 提取預測數據
STEP 3: 抓報價 + Yahoo Finance + 1-2次新聞搜尋。**Binance 報價用一條 bash 迴圈批次抓（省時防漏）**：`for s in BTCUSDT ETHUSDT XAUUSDT XAGUSDT COPPERUSDT XPDUSDT XPTUSDT INTCUSDT NVDAUSDT TSMUSDT MUUSDT AMDUSDT AVGOUSDT QCOMUSDT MSFTUSDT GOOGLUSDT METAUSDT AMZNUSDT TSLAUSDT PLTRUSDT MSTRUSDT EWYUSDT SPYUSDT SPCXUSDT; do echo -n "$s "; curl -s "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=$s" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['lastPrice'],d['priceChangePercent']+'%')"; done`（單檔失敗不擋，續抓）。SuperTrend K線與 Yahoo 宏觀另抓。**★各國公債殖利率必抓（全球流動性風向鏢，債市常領先金銀/股市數小時至數日）**：美10Y(`%5ETNX`)/美30Y(`%5ETYX`)、**日本10Y/30Y JGB、德國10Y Bund**。Yahoo 對日德公債符號常取不到 → 直接 Google News RSS 查最新值(`Japan 10Y JGB yield` / `Germany bund yield` / `global bond rout`)。**重點看「破整數關卡/多年新高/單日大動」**(例：日本10Y破3%=30年新高→全球bond rout→實質利率升壓無息貴金屬+carry trade平倉risk-off)。查到殖利率飆升＝金銀/風險資產可能承壓的領先訊號，寫進 Regime 與風險雷達。
STEP 3.5: 【對抗式解讀驗證，僅在觸發條件成立時執行 — 見下方專節】對報告的因果宣稱做一輪獨立攻擊，攻破的降級為「待查」或補 caveat。**觸發時先跑對抗鏡頭層工具 `event_classifier/lenses.py` 拿機械式紅旗當彈藥**（見 STEP 3.5 執行方式）
STEP 3.6: 【白銀 signals 工具，選配】首次或依賴更新時跑 `cd /Volumes/workplace/EnglishTraining/market-radar/signals && ./setup.sh`；**之後直接 `cd .../signals && .venv/bin/python silver_daily.py`（約5秒；勿用 setup.sh 的 timeout，macOS 無此指令）**。讀 signals/last_run.json，把 tilt/score + COT 空頭多尺度分位帶進 Section 6-B 白銀段當「參考欄」。工具掛掉/取值失敗就標「工具本次未取得」跳過，不擋報告。
STEP 4: 寫 HTML（使用下方 SKELETON TEMPLATE，逐 section 填入）
STEP 5: 更新 reports.json → git add → git commit → git push
```

**品質 > 速度**。10-15 分鐘完成完全可接受。不可為求快省略任何 section。

## 時區校驗規則（最高優先級）

1. 第一步必須 `TZ='Asia/Taipei' date` 確認當前台灣時間。
2. 台灣比美東快 12h（夏令 3-11月）或 13h（冬令）。
3. 週六/週日 → 美國經濟數據全部已公布，搜尋結果非預告。
4. **絕對禁止**把過去事件寫成「今晚」「即將」。
5. 事件日期必須 WebSearch 確認，不可猜測。

## ⛔ 事實 vs 敘事鐵則（最高優先級，違反 = 報告作廢）

**核心原則：每個漲跌的「驅動/原因」都必須基於查證到的事實，不准編故事。寧可寫「原因待查」，也不准模糊給一個聽起來合理但沒查證的理由。**

過往真實犯過的錯誤（都是同一個病根：用敘事取代事實）：
- 把 Fed「維持利率不變」誤寫成「加息」／「暗示加息」——**未查證就下結論**。
- 把黃金「收復 $4,200」吹成「突破歷史新高」——**沒對照前高 $4,410**。
- 一個非農數據就宣稱「降息交易全面確立」「華爾街喊降息」——**把單一數據點過度外推成宏觀共識，且謊稱是華爾街說的**。
- MU 大跌就寫「DRAM 去庫存」——**編的因果，且與現實矛盾**（去庫存=供給過剩=價格跌，但當時記憶體實際供不應求／有廠商爭取貨源）。
- 金銀+晶片同一分鐘同步暴跌，只用 Yahoo Finance search API 查不到新聞，就寫「查無軍事攻擊、僅制裁」——**單一管道查不到 ≠ 沒發生**。實際當時美軍已襲伊朗、伊朗反擊85處美軍基地、川普 NATO 峰會宣布停火作廢，數十家一級媒體同步報導，只是財經 API 抓不到地緣快訊。**用「查無」下否定結論前，必須換多個管道複查。**

**常見框架誤判對照（下因果前逐條自問，防重犯——皆為真實踩過的坑）：**
- **量級對得上嗎**：歸因 DXY/宏觀時，該變數的變動量級要撐得起被解釋的漲跌（曾犯：DXY 只動 0.1-0.5% 卻編「弱美元推金銀+5%」）。量級不足 → 只列次要或寫「驅動待查」。
- **消退 ≠ 反轉**：Fed 政策—「升息押注消退」≠「降息交易啟動」，差一整級；單一數據點只能寫消退，禁寫「降息確立」。
- **軋空 ≠ 利多出盡**：大漲先分機制（軋空=價漲+動能自推+數據前就漲）；是軋空就禁用「利多出盡」，只能寫「動能衰竭」。
- **創高 ≠ 收復失土**：寫「突破/新高/翻多」前對照前高數字；低於前高只能寫「反彈/收復」；「從低點回彈+F&G 極度恐懼」是反證，禁寫「結構翻多」。
- **賣方偏誤**：引投行看多/看空須註明時間戳+是否當前立場，禁單挑一家忽略反向當共識。

**執行規則：**
1. **三層分離**，措辭必須讓讀者分得出來：
   - (a) 查證到的事實 → 可作因果（例：「DXY 抓到 101.12 (+0.26%)」→ 可寫「DXY 反彈壓制黃金」，因兩端都是觀察值）。
   - (b) 未查證的漲跌 → 只能寫「觀察到 X ±Y%，**驅動因素待查證**」。**嚴禁**填入未查證的理由。
   - (c) 我的推測 → 必須明講「這是假設/推測」，與事實分開。
2. **大幅波動強制查證**：任何單日 ±5% 以上的個股/資產，**先查具體新聞/財報/guidance**；查不到就誠實寫「查不到明確催化，跌/漲因未明」，**絕不臆測**。
2b. **多管道查新聞鐵則（違反曾釀成重大誤判）**：新聞查證**絕不可只依賴單一來源**（尤其 Yahoo Finance search API 對地緣政治/突發快訊反應極慢、常抓不到）。**必須至少跨 2-3 個管道**：
   - **Google News RSS**（最重要，對突發/地緣快訊最快）：`https://news.google.com/rss/search?q=關鍵字&hl=en-US&gl=US&ceid=US:en`——回傳各家頭條+時間戳，適合查「川普/伊朗/戰爭/關稅/Fed」等宏觀突發。
   - Yahoo Finance search：`https://query1.finance.yahoo.com/v1/finance/search?q=關鍵字`——偏個股財報，地緣事件常漏。
   - 個別權威源直查（Reuters/CNBC/FT/Barron's）。
   - **鐵則：用「查無 X」下否定結論之前，必須已換過至少 2 個管道**。單一管道查不到只能寫「暫未查到」，不可寫「查無/沒發生」。
   - **跨資產同步暴動＝找共同宏觀觸發**：若多個不相關資產（如金、銀、晶片）在同一時間點同步異動，幾乎必有共同宏觀觸發（地緣/數據/政策），**立即多管道查該時間點的突發新聞**，不可各自編個股理由。
   - **價格先動、新聞後到**：突發事件下價格常領先頭條數分鐘至數十分鐘，查不到即時新聞時，先記錄「價格已反映 X，觸發事件待證」，並持續換管道追。
   - **區辨事件方向與升級**：地緣事件必查清「誰打誰、幾處、是首次還是升級」（例：美軍襲伊朗 vs 伊朗反擊美軍基地，方向相反）；市場只對「實質升級」定價，對「重複的舊聲明」無感（price the escalation, not the statement）。
3. **宏觀敘事需通過反向檢查**：用「去庫存／避險／降息／再通膨」等框架前，先自問「如果這是真的，其他變數該往哪個方向？和現實一致嗎？」矛盾就不准用（例：去庫存 ⇒ 價格應跌＋庫存高，若現實是缺貨漲價則框架錯誤）。
4. **政策/數據性事實（利率決議、CPI、非農、歷史高點）一律以 WebSearch/WebFetch 查證後才寫**，禁止憑記憶或推估當事實。CME FedWatch 機率等數字若沒實際抓到，**不可自己編一個當事實引用**。
5. Section 4 強弱矩陣的「驅動」欄、Section 6 各資產「驅動」、漲跌前三的理由——同樣適用：查證到才寫理由，否則寫「待查」。

## 🔴 STEP 3.5：對抗式解讀驗證（Adversarial Interpretation Review）

**目的**：價格數字抓到就是對的，錯的永遠是「掛在數字上的那句因果」。此環節用獨立視角**專門攻擊、試圖證偽**報告的因果宣稱，防「事實 vs 敘事鐵則」列的病根（編因果、過度擬合單一敘事、把推測當事實、憑記憶寫政策事實）。**這是自審之外的第二層，不是重跑查證。**

### 觸發條件（符合任一才執行；平常日報維持 5-8 分鐘速度，不強制跑）
**先過閘門**：本期是否 (a) 任一資產 ±5%？(b) 有政策/數據事件（利率/CPI/非農/Fed）？(c) 使用者要做持倉決策？**三者皆否＝週末/低資訊日 → 只跑主線程對抗三問（不開 subagent，省成本）；任一為是 → 開獨立 subagent。**
- 報告下了**強因果判斷**（寫「X 導致 Y」而非「觀察到 Y、驅動待查」）
- **市場重大轉折/regime 切換**（如 rotation 破功、結構利空升級、避險回歸、FOMC/數據引爆）
- 使用者**要拿報告做持倉決策**（明講要不要進出場、賭反彈）
- 出現**政策/數據性宣稱**（利率決議、CPI、非農、Fed 主席言論、歷史高點）

### 執行方式
**先跑對抗鏡頭層工具（機械式紅旗，2秒，接在對抗三問之前當彈藥）**：對本期有持倉決策或強因果的標的跑
`cd /Volumes/workplace/EnglishTraining/market-radar/signals && .venv/bin/python event_classifier/lenses.py --asset {SI=F|GC=F|NVDA...} --claim-dir {up|down}（宣稱方向）--holding-dir {short|long}（使用者持倉，無則省略）--note "本期情境"`
它回傳 A 艙規則化紅旗（L1籌碼:漲是真買還逼空/帶寬假象/燃料池；L3技術:長影插針/破位無量；L4總經反向:宣稱方向vs DXY/殖利率矛盾+量級對不對得上）+ 散戶陷阱/心理層（追高殺低/確認偏誤/加碼攤平/參照點，對照使用者老毛病）+ B艙判讀鏡頭該問的攻擊問題。**A艙紅旗是資料算出=可信、可直接寫進報告；B艙裁決仍需主觀判讀。工具掛掉就跳過、不擋報告。**

然後用 **Task tool 開一個獨立 general-purpose subagent** 當對抗 reviewer（獨立視角避免自我確認偏誤），餵給它：本期報告的所有因果宣稱清單 + 查證來源 + 「事實 vs 敘事鐵則」+ **上面鏡頭層算出的紅旗**。要求它逐條攻擊，回傳結構化結果。若情境單純或無 Task tool，至少在主線程用下方三問自我對抗一輪（鏡頭層紅旗仍先跑，當三問的彈藥）。

### 對抗三問（reviewer 逐條問每個因果宣稱）
1. **來源查核**：這個「驅動」有查證來源（新聞/數據）嗎？沒有 → 是否該從「因果」降級成「驅動待查」卻寫死了？
2. **反向檢查**：「若此敘事成立，其他變數該往哪走？和現實矛盾嗎？」（例：純 Fed 殺估值 → 軟體應一起跌，但軟體逆漲 → 敘事不完整，需補「板塊分化」）
3. **更簡解釋**：有沒有更簡單/更接近的解釋，被單一大敘事蓋掉？（例：把個股 -8% 全歸「宏觀」，但其實有個股財報）
4. **量級/分級對得上嗎**：歸因的變數，其變動量級撐得起被解釋的漲跌嗎？（例：DXY 只動 0.1-0.5% 撐不起金銀 +5%）政策/敘事有沒有跳級？（「升息押注消退」被寫成「降息啟動」、「軋空」被寫成「利多出盡」、「反彈」被寫成「翻多」＝跳級，打回原級）

### 裁決與落地
- **CONFIRMED（攻不破，兩端皆查證）** → 因果保留寫進報告。
- **PLAUSIBLE（合理但未完全證實）** → 保留但必須加 caveat（「這是推測」/「待查」）。
- **REFUTED（被反向檢查打破 or 無來源）** → 降級為「驅動待查」，或改寫成更正確的敘事（如補上分化/主次）。
- **報告 footer 或 Section 3 需用一兩句話交代**：本期跑了對抗式驗證、哪些因果 survive、哪些被降級——讓使用者看得到這層把關。

### 誠實鐵則（對抗環節本身也適用）
對抗 reviewer 查不到的，只能說「未能證實此因果」，不可反向編出一個「所以是假的」。攻擊的是「有沒有證據支撐」，不是「用另一個沒查證的敘事取代」。

## 使用者額外指定

$ARGUMENTS

## 核心追蹤資產庫

| 板塊 | 標的 |
|------|------|
| 半導體 | INTC, EWY, MU, QCOM, AVGO, AMD, TSM |
| AI 核心 | NVDA, PLTR, MSFT, GOOGL, META |
| 大型科技 | AMZN, TSLA |
| 指數 | SPY, QQQ |
| 貴金屬/商品 | XAU, XAG, COPPER, XPD, XPT |
| 加密 | BTC, ETH, MSTR, BMNR |
| 亞洲 | ^TWII, EWJ, EWY |

**Binance Futures 完整清單（不可遺漏）**：BTCUSDT, ETHUSDT, XAUUSDT, XAGUSDT, COPPERUSDT, XPDUSDT, XPTUSDT, INTCUSDT, NVDAUSDT, TSMUSDT, MUUSDT, AMDUSDT, AVGOUSDT, QCOMUSDT, MSFTUSDT, GOOGLUSDT, METAUSDT, AMZNUSDT, TSLAUSDT, PLTRUSDT, MSTRUSDT, EWYUSDT, SPYUSDT, SPCXUSDT

## 數據源 & API

| 優先級 | 來源 | 用途 |
|--------|------|------|
| 1 | `https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=XXXUSDT` | 即時報價 |
| 1 | `https://fapi.binance.com/fapi/v1/klines?symbol=XXXUSDT&interval=INTERVAL&limit=320` | SuperTrend K線（XAU/XAG/BTC/ETH 抓 1d+4h+1h） |
| 1 | `https://fapi.binance.com/fapi/v1/fundingRate?symbol=XXXUSDT&limit=1` | Funding Rate |
| 1 | `https://fapi.binance.com/fapi/v1/openInterest?symbol=XXXUSDT` | BTC/ETH OI |
| 2 | Yahoo Finance chart API：`https://query1.finance.yahoo.com/v8/finance/chart/{sym}`（DXY=`DX-Y.NYB`、VIX=`%5EVIX`、10Y=`%5ETNX`、30Y=`%5ETYX`）**勿用 fapi.finance.yahoo.com（錯誤網域會失敗）** | DXY, VIX, MOVE, 30Y, TAIEX, 新聞。取不到 fallback：Google News RSS 查數值 → 標「暫缺」不臆測 |
| 2 | **各國公債殖利率（全球流動性風向鏢，必收）**：美10Y/30Y(Yahoo `%5ETNX`/`%5ETYX`)、**日本10Y/30Y JGB、德國10Y Bund**(Yahoo 常取不到→Google News RSS 查 `Japan 10Y JGB yield`/`Germany bund yield`/`global bond rout`) | 判全球債市拋售(bond rout)、carry trade 平倉、實質利率方向。破整數關卡/多年新高=risk-off 領先訊號 |
| 3 | Alternative.me | 加密 Fear & Greed |
| 4 | Polymarket / CME FedWatch | 預測市場機率 |

## 報告存放規則

- 路徑：`/Volumes/workplace/EnglishTraining/market-radar/reports/YYYY-MM-DD-{am|pm}.html`
- 更新：`/Volumes/workplace/EnglishTraining/market-radar/reports.json` append entry
- Push：`git add → commit → push origin main`
- Repo：`https://github.com/hdchen-course/market-radar.git`

## 分析邏輯核心

### Regime 判定
明確指出：AI Capex Boom / 流動性寬鬆 / 財政主導 / 再通膨 / 滯脹 / 通縮衰退 / 去美元化

### SuperTrend(300,3) 計算
- ATR = RMA(TrueRange, 300)
- Upper = (H+L)/2 + 3×ATR | Lower = (H+L)/2 - 3×ATR
- Close > Upper → LONG | Close < Lower → SHORT
- 三時框（日/4h/1h）共振判定：同多=強多 | 同空=強空 | 背離=盤整

### 各資產 Tactical 模組要求

**A. XAU（先分析）**：ST三框+計分卡(5項:DXY/實質利率/央行購金/ST/地緣)+央行動態+24h預估(ATR公式)+操作table(進場/止損/目標/風報比)+5日情境table+黃金→白銀傳導

**B. XAG（基於黃金推導）**：ST三框+計分卡(7項:DXY/黃金/金銀比/ST/COT/現貨溢價/風險事件)+24h預估+操作table+5日情境+籌碼面(COT/OI/價差)+屬性判定(貨幣or工業)+風控(支撐/插針/止損)

**B 白銀段新增「🔧 signals 工具參考欄」（STEP 3.6 有跑才放，實驗性參考非進場依據）**：從 signals/last_run.json 帶入並顯示——① 工具傾向 tilt + score（偏多/觀望/偏空）；② 觸發訊號 fired（多為空=誠實「不硬找方向」）；③ **COT 空頭多尺度分位**：短空口數 + short_pct26 / short_pct52 / short_pct260 三尺度 + short_range26 全距。**鐵則（照工具 README）**：(a) 必須同時給三尺度 + 全距，禁止只寫單一尺度（26週高/5年低並存是帶寬假象，只寫「92%」會誤讀成空單擁擠）；(b) 標明 COT 落後約10天、只反映報告日結構、不得宣稱抓即時軋空頂底；(c) 明標「工具實驗性、樣本外驗證未完成、僅參考不當進場依據」；(d) 工具傾向與我主觀判斷若衝突，兩者並陳不強行統一，讓使用者看到分歧。

**C. BTC**：ST三框+計分卡(6項:DXY/F&G/FR/OI/美股/鏈上)+24h預估+操作table+5日情境+衍生品(FR/OI/清算/CME Gap)+ETF流

**D. ETH**：ST三框+計分卡(5項:BTC方向/ETH-BTC ratio/FR/OI/催化劑)+24h預估+操作table+5日情境+衍生品

**E. 美股（動態選擇）**：24h漲幅前3+跌幅前3做完整分析（ST+計分卡5項+方向+入場+5日情境+為何被選中）。其餘在快評table（標的/價格/24h%/方向tag/關鍵價位/備註）。

### 預測回溯（Section 0 必做）
讀上期報告 → 比對：
- 24h預估區間 vs 實際（IN/OUT）
- 方向建議 vs 實際漲跌（✅/❌）
- 情境哪個發生了
- 計算命中率 + 教訓

---

## HTML SKELETON TEMPLATE

寫報告時**嚴格按此骨架逐 section 填入**，不可跳過任何 section。

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<!-- [CSS 使用與 2026-06-13-pm.html 相同的完整 style block] -->
</head>
<body>
<div class="container">

<header>
  <h1>終極宏觀流動性 & AI Capex 量化籌碼雷達 V4.5</h1>
  <p class="sub">[日期+時間+版本+一句話主題]</p>
  <div class="badge badge-[regime色]">[REGIME 一句話]</div>
</header>

<!-- ===== SECTION 0: 上期預測回顧 ===== -->
<div class="card full">
  <h2>0. 上期預測回顧（[上期日期]報告）</h2>
  <!-- 命中率 summary + table(標的/預測區間/方向/實際/區間結果/方向結果) + 教訓 -->
</div>

<!-- ===== SECTION 1: 報價面板 ===== -->
<div class="card full">
  <h2>1. 即時報價面板</h2>
  <!-- .price-grid: 全部 25 資產 pi 格子（不可遺漏任何一個） -->
  <!-- 宏觀指標行: DXY/VIX/MOVE/美10Y/美30Y/★日本10Y JGB/★德國10Y Bund/TAIEX/USD-JPY/F&G（各國公債殖利率必列，全球流動性風向鏢） -->
</div>

<!-- ===== SECTION 2: Regime ===== -->
<div class="card full">
  <h2>2. 市場主導 Regime</h2>
  <!-- .mr 行: 核心變數 / 短期 / 中期 / 長期 / Regime判定 -->
</div>

<!-- ===== SECTION 3: 共識 vs Reality ===== -->
<div class="card full">
  <h2>3. 市場共識 vs Reality</h2>
  <!-- table(主題/預期/實際/Mispricing) + .alert 最大Mispricing框 -->
</div>

<!-- ===== SECTION 4: 強弱矩陣 ===== -->
<div class="card full">
  <h2>4. 跨資產強弱矩陣</h2>
  <!-- 全資產 table(#/資產/24h%/ST方向/驅動) 由強到弱 -->
  <!-- 貴金屬+銅列「驅動」欄後標腿別tag(貨幣/工業/軋空/避險),讓腿別分化顯性可比對(例:銅逆跌+白銀漲=白銀非工業腿);其餘資產不強制,勿為湊格子亂貼 -->
</div>

<!-- ===== SECTION 5: 風險雷達 ===== -->
<div class="card full">
  <h2>5. 量化風險雷達</h2>
  <!-- 風險 table(風險/機率/影響/資產/嚴重度bar) -->
  <!-- 操作型態 table(資產/現價/型態tag/依據) — 全焦點資產+XPD+XPT -->
</div>

<!-- ===== SECTION 6: 完整戰術分析 ===== -->
<div class="card full">
  <h2>6. 完整戰術分析</h2>

  <!-- A. XAU tactical-box -->
  <!--   ST帶ATR數字 + 計分卡 + 方向 + 24h(ATR公式) + 操作table + 5日table + 傳導 -->

  <!-- B. XAG tactical-box -->
  <!--   ST + 計分卡7項 + 方向 + 24h + 操作table + 5日table + 籌碼 + 屬性 + 風控 -->

  <!-- C. BTC tactical-box -->
  <!--   ST + 計分卡6項 + 方向 + 24h + 操作table + 5日table + 衍生品段 + 關鍵洞察框 -->

  <!-- D. ETH tactical-box -->
  <!--   ST + 計分卡 + 方向 + 24h + 操作table + 5日table + ETH/BTC分析 -->

  <!-- E. 美股 tactical-box -->
  <!--   漲幅前3 table (每個含完整分析段落: 驅動/ST/方向/入場止損目標/5日情境) -->
  <!--   跌幅前3 table (同上) -->
  <!--   其餘快評 table (標的/價格/24h%/方向tag/關鍵價位/備註) -->

  <!-- F. 🎯持倉紀律提醒 table (實操收尾,使用者唯一直接下單依據): 標的(白銀/EWY/NOK等持倉)/現價/關鍵價位(進場·止損·獲利線)/紀律警語。警語庫:破線認錯別凪、別報復性加空、別預設價位接刀(等訊號)、贏用移動停利讓部位跑完、數據前別重押、集中度風險。此表集中管理→正文各資產段不再重複叮嚀(淨減冗餘) -->
</div>

<!-- ===== SECTION 7: 投行+期權 ===== -->
<div class="card full">
  <h2>7. 投行觀點與期權結構異常</h2>
  <!-- 投行 table(來源/觀點/影響) -->
  <!-- 期權結構 p (VIX結構/GEX/Call Skew/Squeeze信號/散戶vs機構) -->
</div>

<!-- ===== SECTION 8: Calendar ===== -->
<div class="card full">
  <h2>8. 一週核心事件 Calendar（台灣時間）</h2>
  <!-- .tl timeline (每事件: .tl-d日期 + .tl-e事件) -->
  <!-- 關鍵排名 p -->
</div>

<!-- ===== SECTION 9: 情境劇本 ===== -->
<div class="card full">
  <h2>9. 一週情境劇本與機率評估</h2>
  <!-- 預測市場 table -->
  <!-- Base Case (scenario green) -->
  <!-- Bull Case (scenario accent) -->
  <!-- Bear Case (scenario-bear) -->
  <!-- Tail Risk (scenario-tail) -->
</div>

<div class="footer">[disclaimer]</div>

</div>
</body></html>
```

---

## ⚠️ OUTPUT VALIDATION CHECKLIST（寫完 HTML 後必須逐條確認）

在 `Write` HTML 之前，心中逐條驗證以下項目。**任何一項為 NO = 回去補齊再 Write**：

- [ ] Section 0 有 table + 命中率 + 教訓？
- [ ] Section 1 報價面板 ≥ 22 個 .pi 格子？（含 XPT/XPD/SPCX，缺數據標「暫缺」）
- [ ] Section 1 宏觀指標行有 DXY + VIX + 10Y + TAIEX + F&G？
- [ ] Section 2 有 5 行 .mr（核心變數/短/中/長/Regime）？
- [ ] Section 3 有 table + .alert Mispricing 框？
- [ ] Section 4 排序 table ≥ 15 行？貴金屬+銅列驅動後有標腿別tag（貨幣/工業/軋空/避險）？
- [ ] Section 5 風險 table ≥ 4 行 + 操作型態 table ≥ 12 行（含 XPD/XPT）？
- [ ] Section 6-A XAU 有：ST帶數字 + score-card + 24h ATR公式 + 操作table(含風報比) + 5日table + 傳導？
- [ ] Section 6-B XAG 有：ST + score-card 7項 + 操作table + 5日table + 籌碼段 + 屬性段 + 風控段？（+ STEP 3.6 有跑則含 🔧signals工具參考欄：tilt/score + COT空頭三尺度分位+全距 + 實驗性免責，工具沒跑則標「本次未取得」）
- [ ] Section 6-C BTC 有：ST + score-card 6項 + 操作table + 5日table + 衍生品段(FR/OI/清算/CME)？
- [ ] Section 6-D ETH 有：ST + score-card + 操作table + 5日table + ETH/BTC分析？
- [ ] Section 6-E 漲前3 + 跌前3 各有完整分析？+ 其餘快評 table？
- [ ] Section 6-F 🎯持倉紀律提醒 table：涵蓋當前持倉標的（標的/現價/關鍵價位/紀律警語 4欄）？各資產段的重複叮嚀已收斂到此表？
- [ ] Section 7 有投行 table + 期權結構段落？
- [ ] Section 8 有 .tl timeline ≥ 5 事件？
- [ ] Section 9 有 4 個情境（Base/Bull/Bear/Tail）各含具體數字？
- [ ] HTML 總行數 ≥ 400 行？
- [ ] 所有操作 table 都有「風報比」欄？
- [ ] SuperTrend 帶 ATR 數字（不是只寫 LONG/SHORT）？

---

## 分析邏輯補充

### 黃金核心驅動（按重要性）
1. 央行購金（2022後最大變量）
2. 實質利率（TIPS Yield）
3. DXY 美元指數
4. 地緣避險
5. ETF 資金流

### 白銀特殊規則
- 80% 方向由黃金決定 → 必須先完成黃金分析
- 雙屬性：貨幣(跟黃金) vs 工業(跟銅/PMI)
- 判定方法：金銀比收斂=工業主導 | 擴大=貨幣主導
- 搶貨 rumor 極敏感（SHFE庫存+現貨溢價+中國進口）
- 風控：支撐$60/極端$55/爆倉<$50(需XAU<$3K+DXY>105)

### 加密特殊規則
- 注意鏈上真實資金流（非僅價格）
- LTH 行為 + NRPL 零軸位置
- CME Gap 技術意義
- MSTR/BMNR 溢價率 = 機構情緒代理

### DXY 分析規則
不僅報現價，必須含：趨勢方向 / 關鍵價位 / 破位意義 / 對各資產傳導路徑

### ★全球債市 & carry trade 風向鏢（每期必掃，債市常領先金銀/股市）
- **不只看美國**：美10Y/30Y 是基本，但**日本、德國長債**是更靈敏的全球流動性風向鏢。日本是全球最大債權國，**日本長債殖利率飆升 → 日資回流+carry trade 平倉 → 全球流動性收緊 risk-off**（曾漏看：日本10Y破3%=30年新高引爆 global bond rout，金銀連跌，當期報告只歸因 Fed 主席鷹派、漏了債市這個更根本的驅動）。
- **看什麼**：破整數關卡（如日10Y破3%）、多年新高、單日大動、殖利率曲線。全球同步 bond rout = 實質利率齊升 → 壓無息貴金屬（金銀）+ 殺高估值 risk 資產（AI/加密）。
- **傳導鐵則**：金銀無息，實質利率（名目殖利率−通膨預期）是它的最大對手盤之一；殖利率飆升時金銀承壓屬「週期性逆風」，需與「去美元化/財政信譽/央行購金」的結構長多分清——**殖利率逆風是短期、去美元化是長期，別把短期債市逆風誤判成貴金屬結構轉空**。
- **carry trade**：日圓套利交易（借低息日圓買高息資產）是全球風險胃納的槓桿放大器；日本升息/JGB 殖利率飆 → carry 平倉 → 跨資產去槓桿踩踏，是「跨資產同步暴動」的常見隱形觸發，跨資產同步跌時必查日本債市/日圓。

### 事件 Calendar 規則
- 所有時間轉台灣時間(UTC+8)
- 美東 8:30AM = 台灣 20:30 | 美東 2:00PM = 台灣隔天 02:00
- 必須 WebSearch 確認日期，不可猜測
