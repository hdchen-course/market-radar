# claude/ — dailyecreport skill 與 Stop hook 備份（版控）

這裡是 `/dailyecreport` 報告流程的設定備份，進 git 以免本機硬碟壞/誤刪/換機遺失。

## 檔案

| 版控副本 | 本機 live 位置（實際生效處） |
|----------|------------------------------|
| `claude/dailyecreport.md` | `~/.claude/commands/dailyecreport.md` |
| `claude/hooks/check-dailyec-done.py` | `~/.claude/hooks/check-dailyec-done.py`（Stop hook：commit / ±5% 對抗 footer / silver·radar 揭露 / STEP 3.8 五標記 兜底） |
| `claude/hooks/check-macro-oil-geo.py` | `~/.claude/hooks/check-macro-oil-geo.py`（Stop hook：事件級跌勢未查油價/地緣擋下） |
| `claude/hooks/inject-realtime.py` | `~/.claude/hooks/inject-realtime.py`（UserPromptSubmit hook：每回合注入台北/美東真實時間，防時間錯亂、跨 session） |
| `claude/rules/always-check-realtime.md` | `~/.claude/rules/always-check-realtime.md`（全域規則：永遠以注入的真實時間為準、不憑記憶推算） |

## ⚠️ 同步注意（這是備份副本，非 live）

Claude Code 實際讀取的是 `~/.claude/` 下的檔；**這裡是副本，不會自動同步**。
- 改了 live 版 → 記得 `cp` 回這裡再 commit。
- 從這裡還原 → `cp claude/dailyecreport.md ~/.claude/commands/` 、`cp claude/hooks/*.py ~/.claude/hooks/`。
- （若想單一來源免手動同步，可把 `~/.claude/commands/dailyecreport.md` 改為 symlink 指向此檔；代價是 /Volumes 未掛載時 skill 不可用。）

## 刻意未納入

- `~/.claude/settings.json`：含本機/工作環境專屬設定與內部工具 MCP 連線，屬不宜放個人公開庫的內容，**刻意排除**。hook 的註冊方式（Stop / UserPromptSubmit array）請見本機 settings，不在此備份。
- `~/.claude/CLAUDE.md`、`rules/`、`memory/`：個人全域設定與記憶，另行處理。
