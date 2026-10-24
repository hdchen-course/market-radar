"""runlog.py — 工具執行工件（run-ledger），純標準庫。

目的：把 dailyecreport 工具的「有沒有真的跑過」從『我自己貼的標記/數字（自我證言）』
升級成『工具成功跑完才會留下帶時戳的工件』——Stop hook（check-dailyec-done.py Gate E）
據此驗證：報告聲稱某工具跑過時，當天必須有對應的新鮮工件，否則擋 Stop。

每個工具成功算完後呼叫 stamp("<tool>", {可選關鍵數字})。
工件寫到 signals/.last_run/<tool>.json（相對本檔位置，與 cwd 無關），內容：
  {"tool":..., "utc":ISO8601, "epoch":float, "tpe_date":"YYYY-MM-DD"(台北日), "data":{...}}

鐵則：fail-open——stamp 內部任何例外都靜默吞掉，絕不因為寫工件失敗而弄壞工具本身。
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone, timedelta

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_run")
_TPE = timezone(timedelta(hours=8))  # 台北固定 UTC+8


def stamp(tool, data=None):
    """工具成功跑完時呼叫，寫一筆帶時戳工件。永不拋例外。"""
    try:
        os.makedirs(_DIR, exist_ok=True)
        now = time.time()
        rec = {
            "tool": tool,
            "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "epoch": now,
            "tpe_date": datetime.fromtimestamp(now, _TPE).strftime("%Y-%m-%d"),
            "data": data or {},
        }
        with open(os.path.join(_DIR, f"{tool}.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
    except Exception:
        pass  # fail-open：寫工件失敗絕不影響工具


def read(tool):
    """讀某工具工件；不存在/壞檔回 None。供 hook 使用。"""
    try:
        with open(os.path.join(_DIR, f"{tool}.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
