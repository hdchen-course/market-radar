# 終極宏觀流動性、AI 資本支出與量化籌碼雷達 V4.5

## ⚠️ 強制執行流程（違反任何一步 = 報告無效）

```
STEP 1: TZ='Asia/Taipei' date → 確認台灣時間週幾幾點
STEP 2: 讀上一份報告（from reports.json 最後一筆）→ 提取預測數據
STEP 3: 抓報價 + Yahoo Finance + 1-2次新聞搜尋。**Binance 報價用一條 bash 迴圈批次抓（省時防漏）**：`for s in BTCUSDT ETHUSDT XAUUSDT XAGUSDT COPPERUSDT XPDUSDT XPTUSDT INTCUSDT NVDAUSDT TSMUSDT MUUSDT AMDUSDT AVGOUSDT QCOMUSDT MSFTUSDT GOOGLUSDT METAUSDT AMZNUSDT TSLAUSDT PLTRUSDT MSTRUSDT EWYUSDT SPYUSDT SPCXUSDT; do echo -n "$s "; curl -s "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=$s" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['lastPrice'],d['priceChangePercent']+'%')"; done`（單檔失敗不擋，續抓）。SuperTrend K線與 Yahoo 宏觀另抓。**★各國公債殖利率必抓（全球流動性風向鏢，債市常領先金銀/股市數小時至數日）**：美10Y(`%5ETNX`)/美30Y(`%5ETYX`)、**日本10Y/30Y JGB、德國10Y Bund**。Yahoo 對日德公債符號常取不到 → 直接 Google News RSS 查最新值(`Japan 10Y JGB yield` / `Germany bund yield` / `global bond rout`)。**重點看「破整數關卡/多年新高/單日大動」**(例：日本10Y破3%=30年新高→全球bond rout→實質利率升壓無息貴金屬+carry trade平倉risk-off)。查到殖利率飆升＝金銀/風險資產可能承壓的領先訊號，寫進 Regime 與風險雷達。**★信用利差同步抓（AI capex 可持續性/違約風向鏢，2026/10 CoreWeave 信用危機後新增）**：FRED 高收益利差 HY OAS(`https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2`，csv 取最後一筆、日頻 T+1、無需 key) + 投資級 IG OAS(`BAMLC0A0CM`)；Yahoo 抓 HYG/JNK(高收益債 ETF)、CRWV(CoreWeave，AI 基建信用個股)。**判讀鐵則：HY OAS 走闊=違約/信用壓力升；★HY 動、IG 不動=壓力局部鎖在高收益/AI 端(可控)；HY+IG 齊飆=系統性 risk-off 升級(carry 平倉/去槓桿)，是金/加密從承接變被拖下水的觸發線**。HY OAS 單日 +10bps 或破關卡(3.5%/4%) 寫進 Regime 與風險雷達。
STEP 3.5: 【對抗式解讀驗證，僅在觸發條件成立時執行 — 見下方專節】對報告的因果宣稱做一輪獨立攻擊，攻破的降級為「待查」或補 caveat。**觸發時先跑對抗鏡頭層工具 `event_classifier/lenses.py` 拿機械式紅旗當彈藥**（見 STEP 3.5 執行方式）
STEP 3.6: 【白銀 signals 工具，必跑（唯一例外＝工具報錯並貼訊息）】首次或依賴更新時跑 `cd /Volumes/workplace/EnglishTraining/market-radar/signals && ./setup.sh`；**之後直接 `cd .../signals && .venv/bin/python silver_daily.py`（約5秒；勿用 setup.sh 的 timeout，macOS 無此指令）**。讀 signals/last_run.json，把 tilt/score + COT 空頭多尺度分位帶進 Section 6-B 白銀段當「參考欄」。**每期必跑；唯一可不跑＝工具執行回報錯誤**，則於 6-B 標「工具本次報錯：<貼錯誤訊息>」後續跑其餘步驟；**非報錯不得以「選配/省時/今天不需要」為由略過或標「未取得」**。
STEP 3.7: 【盤面判讀引擎 radar.py，必跑（唯一例外＝工具報錯並貼訊息）】跑 `cd /Volumes/workplace/EnglishTraining/market-radar/signals && python3 radar.py BTCUSDT && python3 radar.py ETHUSDT`（純標準庫、約5-10秒；可再擴跑持倉籃其他幣安標的如 AAVEUSDT/MSTRUSDT）。它整合 多尺度CVD + Volume Profile籌碼區 + SuperTrend三框 + funding/OI擁擠度(含歷史分位) + 宏觀層(10Y/DXY/VIX/HY信用利差) + K線形態×位置交互，加權強度評分輸出『主劇本(偏多/區間/偏空+信心) + 偏多偏空各自為什麼(強度×權重) + 需要盯哪些數據』。**★自動帶入：直接跑 `python3 radar.py BTCUSDT --html`（ETH 同理）輸出可貼進 6-C/6-D 的 `<div class="radar-draft">` 底稿欄片段，省手抄**。把它當**客觀底稿**帶進 Section 6-C(BTC)/6-D(ETH)，與我的情境判讀**並陳**。★鐵則：radar 是規則化客觀層、權重/門檻為經驗值(回測見 signals/backtest.py)，**抓不到當日催化(財報/MSCI指數調整/地緣/新聞)**，那層仍須我多管道查證補上；引擎劇本與我情境判讀衝突時兩者並陳、不強行統一。**每期必跑 BTC+ETH 兩個 `--html`；唯一可不跑＝工具回報錯誤**，則於 6-C/6-D 標「radar 本次報錯：<錯誤訊息>」後續跑；**非報錯不得略過或標「未取得」**。詳見 signals/RADAR.md。
STEP 3.8: 【型態走勢與支撐壓力——五大標的必報】每期必為 **XAU / XAG / SOXX / BTC / MSTR** 各報四件：① **K 線型態走勢判讀**（純標準庫 `signals/patterns.py`，66 型態取代 TA-Lib；BTC 已含於 radar，**XAU/XAG/MSTR 用幣安 XAUUSDT/XAGUSDT/MSTRUSDT 跑 `python3 radar.py <sym> --html`**，**SOXX 無幣安永續→抓 Yahoo 日線 OHLC 餵 `patterns.scan`/`detect_last`**，報具名型態+方向 bias）；② **SuperTrend 三框方向**；③ **支撐/壓力區**（幣安標的用 radar 的 Volume Profile POC/VAH/VAL，或跑 `python3 vpvr.py <sym>` 取更完整 VPVR：POC/VA70%/HVN/LVN；**SOXX 抓 Yahoo 日線 OHLCV 餵 `vpvr.vpvr()`** 取 POC/VA/HVN/LVN，退而求其次才用 swing 高低+整數關卡）；④ **多空機會衡量**（型態 bias + ST + S/R + 當日催化綜合，必寫成條件式「站上/跌破 X 才偏多/偏空」，不報死）。寫進對應 Section 6；**SOXX/MSTR 同樣必報滿四件、不得降為三件**（放不進 tactical-box 就在 6-E/6-F 新增小段；SuperTrend 三框對 SOXX 用 Yahoo 日線 OHLC 自算、對 MSTR 用幣安 MSTRUSDT klines）。**每標的必報；唯一可不報＝該標的工具實際回報錯誤，則貼出錯誤訊息後續跑其餘標的。非報錯不得以「選配／省時／低資訊日／情境單純／型態沒變／已折入先前判讀／超時」為由略過或標「未取得／暫缺」。** **★低資訊日/週末/低量日亦必報滿五標的四件——STEP 3.5 的低資訊日降級只適用對抗層，不適用 3.8。** **★SOXX 專屬鐵則：Yahoo OHLC 抓取或 patterns/vpvr 執行若失敗，必須貼出實際錯誤訊息（HTTP 碼或 traceback），不得僅以「暫缺」帶過——對 3.8 型態四件而言「暫缺」不是合法狀態，只有「貼出的工具錯誤」才是（價格面板可標暫缺、型態判讀不可）。** **★BTC 若 radar 報錯，改直接以幣安 BTCUSDT klines 餵 patterns.scan/detect_last 補出型態四件，不得因 radar 報錯連帶略過 BTC。** **★每標的在其 3.8 區塊輸出機械標記 HTML 註解 `<!--3.8:SYM-->`（SYM∈XAU/XAG/SOXX/BTC/MSTR，五個都要）供 DONE GATE 與 Stop hook 驗證；該標的工具實際報錯則改輸出 `<!--3.8:SYM:na-->` 並貼錯誤訊息。缺任一標記＝報告未完成。** patterns 定義經紅隊對照 TA-Lib/Nison 稽核、回測未做＝當客觀底稿非進場依據。
STEP 4: 寫 HTML（使用下方 SKELETON TEMPLATE，逐 section 填入）
STEP 5: 更新 reports.json → git add → git commit → git push origin main（完成後**必過檔末 STEP 6 DONE GATE**：貼出 commit hash 與 push 結果；**只寫完 HTML 未實際 commit/push＝報告無效、不得宣稱完成**）
```

**品質 > 速度**。單一時間預算：10-15 分鐘完成完全可接受，低資訊日亦同。**不得以「5-8 分鐘」「省時」「省成本」「怕超時」為由省略任何 section、STEP 3.5 獨立 subagent、或 STEP 3.6/3.7 工具**。速度優化只能靠內文精煉，不能靠跳步。

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
   - **跨資產同步暴動＝找共同宏觀觸發**：若多個不相關資產（如金、銀、晶片）在同一時間點同步異動，幾乎必有共同宏觀觸發（地緣/數據/政策），**立即多管道查該時間點的突發新聞**，不可各自編個股理由。**★硬性執行檢查（曾漏，2026-09-01 白銀/黃金/股/債同步殺卻只歸因 Fed 鷹派、漏了中東升級→油價→通膨→bond rout）：股/債/金同步大動時，下宏觀因果結論前『必先』跑① 油價(`CL=F`/`BZ=F`，Yahoo 取不到用 Google News RSS)② 地緣/政策突發(`Middle East`/`OPEC`/`關稅`/`戰爭`/中東 + Google News RSS)③ 各國長債殖利率(日/英/德)——三者都查完才准寫因果。已設 Stop hook `check-macro-oil-geo.py` 兜底：產含事件級跌勢字的報告卻沒查油價/地緣會被擋下。**
   - **價格先動、新聞後到**：突發事件下價格常領先頭條數分鐘至數十分鐘，查不到即時新聞時，先記錄「價格已反映 X，觸發事件待證」，並持續換管道追。
   - **區辨事件方向與升級**：地緣事件必查清「誰打誰、幾處、是首次還是升級」（例：美軍襲伊朗 vs 伊朗反擊美軍基地，方向相反）；市場只對「實質升級」定價，對「重複的舊聲明」無感（price the escalation, not the statement）。
3. **宏觀敘事需通過反向檢查**：用「去庫存／避險／降息／再通膨」等框架前，先自問「如果這是真的，其他變數該往哪個方向？和現實一致嗎？」矛盾就不准用（例：去庫存 ⇒ 價格應跌＋庫存高，若現實是缺貨漲價則框架錯誤）。
4. **政策/數據性事實（利率決議、CPI、非農、歷史高點）一律以 WebSearch/WebFetch 查證後才寫**，禁止憑記憶或推估當事實。CME FedWatch 機率等數字若沒實際抓到，**不可自己編一個當事實引用**。
5. Section 4 強弱矩陣的「驅動」欄、Section 6 各資產「驅動」、漲跌前三的理由——同樣適用：查證到才寫理由，否則寫「待查」。

## 🔴 STEP 3.5：對抗式解讀驗證（Adversarial Interpretation Review）

**目的**：價格數字抓到就是對的，錯的永遠是「掛在數字上的那句因果」。此環節用獨立視角**專門攻擊、試圖證偽**報告的因果宣稱，防「事實 vs 敘事鐵則」列的病根（編因果、過度擬合單一敘事、把推測當事實、憑記憶寫政策事實）。**這是自審之外的第二層。**「不是重跑查證」＝不必重抓價格/新聞，**但仍必須以獨立視角重新攻擊因果，不得把先前 research 的結論直接當作已通過對抗驗證而「折入」。**

### 觸發條件（閘門任一為是＝強制執行；閘門皆否才得降為主線程三問。無論哪種，對抗層本身一律必跑，不存在「不強制跑」）
**先過閘門（機械判定、無裁量；逐條只能用下列客觀事實回答，不得用「感覺今天單純」略過）**：
- (a) STEP 3 批次報價中，追蹤資產庫任一標的 **|24h%| ≥ 5.0** →【是】。
- (b) 本報告 Section 8 Calendar 當日(台灣時間)列有、或 Google News RSS 當日查到任一：FOMC/利率決議、CPI/PCE、非農、Fed 官員正式談話、關稅/地緣突發 →【是】。**(b) 必須先查 Calendar 與 RSS 後才能回答，不得憑印象答「否」。**
- (c) $ARGUMENTS 或本 session 對話出現任何進場/出場/加碼/減碼/「要不要賭反彈」等持倉動作詞 →【是】。
**裁決**：三者皆為【否】（且已逐條查證）＝ 低資訊日，得只跑主線程對抗三問。**只要任一為【是】＝ 必須開獨立 Task subagent 跑對抗式驗證，不得以「情境單純」「省成本」「超時」「已在 research 查過/折入先前結論」為由降級成主線程——唯一例外＝Task/Agent 工具實際回報錯誤，且須在報告 footer 貼出該錯誤訊息。**
- 報告下了**強因果判斷**（寫「X 導致 Y」而非「觀察到 Y、驅動待查」）
- **市場重大轉折/regime 切換**（如 rotation 破功、結構利空升級、避險回歸、FOMC/數據引爆）
- 使用者**要拿報告做持倉決策**（明講要不要進出場、賭反彈）
- 出現**政策/數據性宣稱**（利率決議、CPI、非農、Fed 主席言論、歷史高點）

### 執行方式
**先跑對抗鏡頭層工具（機械式紅旗，2秒，接在對抗三問之前當彈藥）**：對本期有持倉決策或強因果的標的跑
`cd /Volumes/workplace/EnglishTraining/market-radar/signals && .venv/bin/python event_classifier/lenses.py --asset {SI=F|GC=F|NVDA...} --claim-dir {up|down}（宣稱方向）--holding-dir {short|long}（使用者持倉，無則省略）--note "本期情境"`
它回傳 A 艙規則化紅旗（L1籌碼:漲是真買還逼空/帶寬假象/燃料池；L3技術:長影插針/破位無量；L4總經反向:宣稱方向vs DXY/殖利率矛盾+量級對不對得上）+ 散戶陷阱/心理層（追高殺低/確認偏誤/加碼攤平/參照點，對照使用者老毛病）+ B艙判讀鏡頭該問的攻擊問題。**A艙紅旗是資料算出=可信、可直接寫進報告；B艙裁決仍需主觀判讀。工具掛掉就跳過、不擋報告。**

然後：**閘門任一為【是】時，必用 Task tool 開一個獨立 general-purpose subagent** 當對抗 reviewer（獨立視角避免自我確認偏誤），餵給它：本期報告的所有因果宣稱清單 + 查證來源 + 「事實 vs 敘事鐵則」+ **上面鏡頭層算出的紅旗**。要求它逐條攻擊，回傳結構化裁決。**此步不得以「情境單純」「已在 research 階段查過」「折入先前結論」「省成本」「超時」為由降級成主線程三問——唯一例外＝Task/Agent 工具實際回報錯誤，且須在 footer 貼出錯誤訊息。** 閘門皆【否】時，才改用主線程下方三問自我對抗一輪。**鏡頭層紅旗兩種情況都先跑。**

### 對抗三問（reviewer 逐條問每個因果宣稱）
1. **來源查核**：這個「驅動」有查證來源（新聞/數據）嗎？沒有 → 是否該從「因果」降級成「驅動待查」卻寫死了？
2. **反向檢查**：「若此敘事成立，其他變數該往哪走？和現實矛盾嗎？」（例：純 Fed 殺估值 → 軟體應一起跌，但軟體逆漲 → 敘事不完整，需補「板塊分化」）
3. **更簡解釋**：有沒有更簡單/更接近的解釋，被單一大敘事蓋掉？（例：把個股 -8% 全歸「宏觀」，但其實有個股財報）
4. **量級/分級對得上嗎**：歸因的變數，其變動量級撐得起被解釋的漲跌嗎？（例：DXY 只動 0.1-0.5% 撐不起金銀 +5%）政策/敘事有沒有跳級？（「升息押注消退」被寫成「降息啟動」、「軋空」被寫成「利多出盡」、「反彈」被寫成「翻多」＝跳級，打回原級）

### 裁決與落地
- **CONFIRMED（攻不破，兩端皆查證）** → 因果保留寫進報告。
- **PLAUSIBLE（合理但未完全證實）** → 保留但必須加 caveat（「這是推測」/「待查」）。
- **REFUTED（被反向檢查打破 or 無來源）** → 降級為「驅動待查」，或改寫成更正確的敘事（如補上分化/主次）。
- **報告 footer 必含對抗式驗證裁決段（此為 STEP 6 DONE GATE B 項硬性檢查，缺此段＝報告未完成）**：列出本期閘門 (a)(b)(c) 各自是/否、是否開了獨立 subagent、哪些因果 CONFIRMED / 哪些 PLAUSIBLE（已加 caveat）/ 哪些 REFUTED（已降級為待查）——讓使用者看得到這層把關。

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
| 2 | **信用利差（AI capex/違約風向鏢，必收）**：FRED HY OAS(`fredgraph.csv?id=BAMLH0A0HYM2`)、IG OAS(`BAMLC0A0CM`)，csv 取最後一筆、日頻 T+1、無需 key；Yahoo HYG/JNK/CRWV | 判 AI 基建信用壓力/違約風險。HY 走闊+IG 穩=局部；HY+IG 齊飆=系統性 |
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

**C. BTC**：ST三框+計分卡(6項:DXY/F&G/FR/OI/美股/鏈上)+24h預估+操作table+5日情境+衍生品(FR/OI/清算/CME Gap)+ETF流。**+ STEP 3.7 有跑則附「🛰️ radar 客觀底稿欄」**：radar.py 的主劇本(偏多/區間/偏空) + 偏多偏空各自為什麼 + 需要盯的數據，與我情境判讀並陳(引擎=規則客觀層、我補情境催化；兩者衝突不強行統一)。ETH(6-D)同理。

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
  <!-- 宏觀指標行: DXY/VIX/MOVE/美10Y/美30Y/★日本10Y JGB/★德國10Y Bund/★HY信用利差/★IG信用利差/TAIEX/USD-JPY/F&G（各國公債殖利率+信用利差必列，全球流動性+信用風向鏢） -->
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
- [ ] **STEP 3.8 五標的（XAU/XAG/SOXX/BTC/MSTR）各有「型態走勢(patterns 具名型態+方向) + SuperTrend三框 + 支撐壓力區(VP POC/VAH/VAL 或 swing高低) + 多空機會(條件式)」四件？**（工具報錯才可缺，須貼訊息）
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
- **傳導鐵則**：金銀無息，**實質利率（名目殖利率−通膨預期，抓 TIPS `DFII10`）是它的最大對手盤**——判金銀方向時看實質利率比看名目 10Y 更準（名目升但通膨預期也升時金銀未必跌，真正壓金銀的是實質利率升）。殖利率飆升時金銀承壓屬「週期性逆風」，需與「去美元化/財政信譽/央行購金」的結構長多分清——**殖利率逆風是短期、去美元化是長期，別把短期債市逆風誤判成貴金屬結構轉空**。
- **★短端 vs 長端（別把債市都歸因 Fed）**：Fed 升不升息主要控**短端(2Y)**；**長端(10Y/30Y)是市場對財政赤字+發債供給+通膨+期限溢價的定價，Fed 未必控得住**（例：Bessent 財政部回購想壓長端、30Y 仍彈回 5%+）。所以「債市問題」常是財政失控/供需/信心，非 Fed 政策——分析長端跌時先問「是 Fed 預期，還是財政/供給/避險？」別一律歸 Fed。長端=政府融資成本+房貸+金融條件，**是政策層(財政部/白宮)真正痛點**（政治上極怕長端失控），故長端飆升的政治與市場衝擊常大於短端。
- **carry trade**：日圓套利交易（借低息日圓買高息資產）是全球風險胃納的槓桿放大器；日本升息/JGB 殖利率飆 → carry 平倉 → 跨資產去槓桿踩踏，是「跨資產同步暴動」的常見隱形觸發，跨資產同步跌時必查日本債市/日圓。

### ★信用利差風向鏢（AI capex 時代新增，2026/10 CoreWeave 信用危機後列為必掃）
- **為什麼看**：AI 基礎設施熱潮的最大尾部風險是「capex 可持續性/變現能力 gap」——當 AI 算力租賃商（如 CoreWeave）債券跌到困境水平，代表信用市場開始定價償債風險，是比股價更冷靜的示警。NVDA 等晶片商常是這些客戶的股東（循環融資），信用事件會反噬晶片鏈（曾實證：2026/10 CoreWeave 單週 -25%、債券跌到困境價，費半連跌 8 日創 2008 來最長）。
- **看什麼**：① FRED HY OAS（高收益利差，最正宗，走闊=違約 risk 升）；② IG OAS（投資級）當對照；③ HYG/JNK ETF 即時情緒；④ CRWV 個股。
- **★分級鐵則（判 rotation 會不會變全面去槓桿）**：**HY 走闊、IG 不動 = 壓力局部鎖在高收益/AI 端（板塊 de-rate、可控，金/加密仍可當避險承接）**；**HY+IG 齊飆 = 信用壓力外溢成系統性 risk-off（carry 平倉/去槓桿升級），此時金/加密會從承接變被拖下水——這是 Bear/Tail 情境的客觀觸發線**。
- **傳導**：HY OAS 單日 +10bps 或破整數關卡（3.5%/4%/5%）= 信用壓力升級，寫進 Regime/風險雷達；與殖利率、油價並列為三大宏觀領先訊號。切勿把 CEO/賣方「終將過去」喊話當底部訊號（賣方偏誤），底看 HY 利差止穩 + 困境個股債券止血。

### 事件 Calendar 規則
- 所有時間轉台灣時間(UTC+8)
- 美東 8:30AM = 台灣 20:30 | 美東 2:00PM = 台灣隔天 02:00（★夏令；2026-11-02 起冬令 +1h：收盤台灣 05:00、8:30 數據=台灣 21:30、FOMC 14:00=台灣隔天 03:00）
- 必須 WebSearch 確認日期，不可猜測

---

## ✅ STEP 6：DONE GATE（收尾硬閘——在 commit 之後、宣稱「完成」之前逐條確認；任一 NO ＝ 報告未完成、無效，不得宣稱完成）

> 設立原因：3.5 獨立 subagent、3.6/3.7 工具、STEP 5 commit/push 長期缺「無裁量強制語＋收尾驗證」，被「選配/建議/情境單純/省時」規避。此 gate 是唯一的「完成」定義，並有 Stop hook `check-dailyec-done.py` deterministic 兜底（±5% 無對抗 footer / 報告未 commit / reports.json 未 append → 擋 Stop）。

**A. 產出落地**
- [ ] HTML 已 Write 到 `reports/YYYY-MM-DD-{am|pm}.html`
- [ ] `reports.json` 已 append 本期 entry（date/type/file）
- [ ] 已實際執行 `git add` + `git commit`（**貼出 commit hash**）
- [ ] 已實際執行 `git push origin main`（貼出 push 結果或 `git status` up to date）
- ※ 只寫完 HTML 未 commit/push ＝ 本報告未完成、無效。

**B. 對抗式驗證（STEP 3.5）**
- [ ] 已跑閘門三問、並在報告寫出 (a)(b)(c) 各自【是/否】與依據。
- [ ] 閘門任一【是】：footer 含**獨立 subagent** 裁決段，逐條列 CONFIRMED/PLAUSIBLE/REFUTED。缺此段＝未完成。
- [ ] 閘門皆【否】：footer 註明「低資訊日，主線程三問，無獨立 subagent」。

**C. 三個工具狀態（每個二擇一、不得留白、不得以「選配」略過）**
- [ ] `lenses.py`：有跑（貼紅旗摘要）／或貼出工具錯誤訊息。
- [ ] `silver_daily.py`：有跑（6-B 含三尺度分位+全距）／或貼出錯誤訊息。
- [ ] `radar.py`（BTC+ETH）：有跑（6-C/6-D 含 radar-draft 欄）／或貼出錯誤訊息。
- ※ 「選擇不跑」不是合法狀態；唯一合法的「沒跑」＝工具回報錯誤且已貼訊息。

**D. STEP 3.8 五標的型態/支撐壓力/多空（每個二擇一、不得留白、不得以「選配/低資訊日/情境單純/省時/SOXX要另抓/型態沒變/折入先前」略過）**
- [ ] XAU：型態(具名)＋SuperTrend三框＋支撐壓力(POC/VAH/VAL 或 swing)＋多空條件式 四件齊，且輸出 `<!--3.8:XAU-->` 標記／或工具報錯貼訊息＋`<!--3.8:XAU:na-->`。
- [ ] XAG：同上四件＋`<!--3.8:XAG-->`／或 `:na`＋錯誤訊息。
- [ ] SOXX：同上四件(Yahoo OHLC 餵 patterns/vpvr)＋`<!--3.8:SOXX-->`／或 `:na`＋**實際**錯誤訊息（SOXX 不得僅標「暫缺」）。
- [ ] BTC：同上四件(可取自 radar；radar 報錯改幣安 klines 餵 patterns)＋`<!--3.8:BTC-->`／或 `:na`。
- [ ] MSTR：同上四件＋`<!--3.8:MSTR-->`／或 `:na`。
- ※ 四件不得降為三件；缺任一標記＝未完成。有 Stop hook `check-dailyec-done.py` D 段 deterministic 兜底（五標記缺任一且無 `:na` 揭露＝擋 Stop）。
