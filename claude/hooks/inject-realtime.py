#!/usr/bin/env python3
"""UserPromptSubmit hook：每回合把「真實世界時間」注入 context，杜絕時間錯亂。

背景：Claude 常憑對話/記憶推算當前時間而出錯（把過去事件當「今晚」、用過期報價、
算錯 session 盤別、chartPreviousClose 當日線基準…）。此 hook 於每次使用者送出 prompt 時
印出當下真實時間，內容會被納入該回合 context → Claude 每回合都「看得到」正確時間，
不需要也不應該再憑記憶猜。跨 session 生效（註冊於 settings.json 的 UserPromptSubmit）。

鐵則：fail-open。任何例外都靜默結束（不輸出、不擋），絕不因此 hook 影響正常互動。
"""
import sys

try:
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        tw = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S %A")
        et = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M %A %Z")
    except Exception:
        # 無 zoneinfo/tzdata 時退回系統本地時間（至少有個真實時戳）
        local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tw = local + "（系統本地時區）"
        et = "暫缺"
    print(f"[realtime] 當前真實時間 — 台北 {tw} ｜ 美東 {et}。"
          "以此為準，勿憑記憶/對話推算當前時間或盤別；做時間敏感動作"
          "（報告/即時報價/排程/事件日期判斷）前，如與上述有出入請先重跑 "
          "`TZ='Asia/Taipei' date` 複核。")
except Exception:
    pass

sys.exit(0)
