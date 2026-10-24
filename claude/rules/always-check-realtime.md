# 最高優先：永遠以真實世界時間為準，不憑記憶/對話推算

<EXTREMELY_IMPORTANT>
時間錯亂是反覆踩過的坑（把過去事件寫成「今晚/即將」、用過期報價、算錯美股盤別、
用 chartPreviousClose 當日線基準…）。以下規則對**所有任務**（不只報告）MANDATORY：

1. **每回合都有真實時間注入**：UserPromptSubmit hook `inject-realtime.py` 會在每個回合開頭印出
   `[realtime] 當前真實時間 — 台北 … ｜ 美東 …`。**那就是當前真實時間的事實來源，永遠以它為準。**
2. **禁止憑對話/記憶推算「現在幾點/今天星期幾/哪個盤別/某事件是過去還未來」**。對話裡的舊時戳、
   summary、你自己上一則訊息的時間，都不是「現在」。
3. **時間敏感動作前必核對注入時間**：產報告、判即時報價新舊、排程、判斷經濟事件/財報是過去或未來、
   算美股當盤 vs 盤前/盤後——動作前先看本回合 `[realtime]`；若不確定或與手上資料衝突，
   **重跑 `TZ='Asia/Taipei' date`（必要時 `TZ='America/New_York' date`）複核後才動作**。
4. **冬令/夏令**：美東時區由系統 zoneinfo 處理（EDT↔EST 自動），2026-11-02 起美東轉 EST、
   台北與美東差 13h（夏令 12h）；換算美股開收盤時間以注入的美東時戳為準。
5. **hook 沒出現時**（被關/報錯）：不得當作「免檢查」，改**主動**先跑 `TZ='Asia/Taipei' date` 再動作。

dailyecreport 的 STEP 1（TZ date 確認）與此一致，為其在報告流程的具體落實。
此規則跨 session 生效（本檔每 session 載入 + hook 註冊於 settings.json）。
</EXTREMELY_IMPORTANT>
