# claude/ — dailyecreport skill 與 Stop hook 備份（版控）

這裡是 `/dailyecreport` 報告流程的設定備份，進 git 以免本機硬碟壞/誤刪/換機遺失。

## 檔案

| 版控副本 | 本機 live 位置（實際生效處） |
|----------|------------------------------|
| `claude/dailyecreport.md` | `~/.claude/commands/dailyecreport.md` |
| `claude/hooks/check-dailyec-done.py` | `~/.claude/hooks/check-dailyec-done.py`（Stop hook：commit / ±5% 對抗 footer / silver·radar 揭露 / STEP 3.8 五標記 兜底） |
| `claude/hooks/check-macro-oil-geo.py` | `~/.claude/hooks/check-macro-oil-geo.py`（Stop hook：事件級跌勢未查油價/地緣擋下） |

## ⚠️ 同步注意（這是備份副本，非 live）

Claude Code 實際讀取的是 `~/.claude/` 下的檔；**這裡是副本，不會自動同步**。
- 改了 live 版 → 記得 `cp` 回這裡再 commit。
- 從這裡還原 → `cp claude/dailyecreport.md ~/.claude/commands/` 、`cp claude/hooks/*.py ~/.claude/hooks/`。
- （若想單一來源免手動同步，可把 `~/.claude/commands/dailyecreport.md` 改為 symlink 指向此檔；代價是 /Volumes 未掛載時 skill 不可用。）

## 刻意未納入

- `~/.claude/settings.json`：含本機/公司內部 MCP 設定（Amazon builder-mcp 等），屬公司內容，依個人公開庫不放公司內容原則**排除**。hook 的註冊方式（Stop array）請見本機 settings，不在此備份。
- `~/.claude/CLAUDE.md`、`rules/`、`memory/`：個人全域設定與記憶，另行處理。
