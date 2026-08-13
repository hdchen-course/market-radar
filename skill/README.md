# skill/ — dailyecreport 技能定義（版本備份）

`dailyecreport.md` 是 `/dailyecreport` 這個 Claude Code 技能的完整定義，放進 repo 做版控備份，跟它驅動的工具（`signals/`、`signals/event_classifier/`）放一起。

**執行用的實體檔在**：`~/.claude/commands/dailyecreport.md`（Claude Code 讀這份）。
本目錄是同步副本——**改動請以 `~/.claude/commands/` 為準，改完再 `cp` 過來 commit**，兩邊別各改各的。

## 技能串起的工具
- `signals/silver_daily.py` — 白銀每日傾向（STEP 3.6）
- `signals/event_classifier/backtest_drift.py` — pre-event drift 回測（階段1）
- `signals/event_classifier/lenses.py` — 對抗鏡頭層（STEP 3.5，觸發時跑，拿機械式紅旗當彈藥）
