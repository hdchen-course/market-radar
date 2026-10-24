#!/usr/bin/env python3
"""Stop hook: /dailyecreport 收尾 DONE GATE 的 deterministic 兜底。

背景：skill 的 STEP 3.5 獨立 subagent、STEP 3.6/3.7 工具、STEP 5 commit/push 長期
靠自律，被「選配/情境單純/省時」規避。此 hook 用 filesystem/git/HTML regex 做無裁量驗證：
只在「今天(台灣時間)有 reports/YYYY-MM-DD-*.html」時作動，否則立即放行、絕不干擾非報告 session。

擋三缺口（任一不合規 → 經 stdout JSON decision:block 擋 Stop，要求補做）：
  A. 今日報告寫了但未 git commit / 或未 append reports.json。
  B. 報告面板有任一資產 |24h%|≥5 卻全文無對抗裁決(「對抗」+ CONFIRMED/PLAUSIBLE/REFUTED)。
  C. 6-B 白銀 signals / 6-C+6-D radar 欄既無工具輸出也無「未取得/報錯」揭露＝靜默略過。

鐵則：A 只閘本機 commit(必達成)不閘 push(需網路/auth,避免 wedge)；所有缺口都「可當場補做」,
補完再 Stop 即通過,不會 livelock。任何例外/讀不到 → fail-open(exit 0,不擋),絕不因 hook bug 卡死。
"""
import json
import sys
import os
import re
import glob
import subprocess
from datetime import datetime, timezone, timedelta

REPO = "/Volumes/workplace/EnglishTraining/market-radar"


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def main():
    # 台灣時間今天
    tw = timezone(timedelta(hours=8))
    today = datetime.now(tw).strftime("%Y-%m-%d")

    rdir = os.path.join(REPO, "reports")
    todays = sorted(glob.glob(os.path.join(rdir, f"{today}-*.html")))
    if not todays:
        return  # 今天沒出報告 → 放行

    newest = todays[-1]
    try:
        html = open(newest, encoding="utf-8").read()
    except Exception:
        return

    rels = [os.path.relpath(f, REPO) for f in todays]

    # ---- A. git commit + reports.json ----
    try:
        porcelain = subprocess.run(
            ["git", "-C", REPO, "status", "--porcelain", "--", "reports/", "reports.json"],
            capture_output=True, text=True, timeout=15).stdout
    except Exception:
        porcelain = None
    if porcelain is not None:
        dirty = []
        for ln in porcelain.splitlines():
            path = ln[3:].strip() if len(ln) > 3 else ""
            for rel in rels:
                if path.endswith(os.path.basename(rel)):
                    dirty.append(os.path.basename(rel))
        if dirty:
            block("【DONE GATE A】今日報告 " + "、".join(sorted(set(dirty))) +
                  " 已寫出但 git 顯示未 commit（STEP 5=更新 reports.json→git add→commit→push）。"
                  "請 git add + commit（本機 commit 即解除；push 另計）後再收工。")
            return

    # reports.json 是否 append
    try:
        rj = json.load(open(os.path.join(REPO, "reports.json"), encoding="utf-8"))
        listed = {e.get("file") for e in rj}
        missing = [rel for rel in rels if rel not in listed]
        if missing:
            block("【DONE GATE A】報告 " + "、".join(missing) +
                  " 未寫入 reports.json。請 append entry(date/type/file)後再收工。")
            return
    except Exception:
        pass  # reports.json 讀不到 → 不因此擋

    # ---- B. ±5% → 對抗裁決 footer ----
    try:
        # 掃價格面板(ch) + 強弱矩陣/內文(td class=pos/neg) 的百分比，補矩陣表盲區
        pcts = [abs(float(x)) for x in
                re.findall(r'class="[^"]*\b(?:ch|pos|neg)\b[^"]*">\s*([+-]?\d+(?:\.\d+)?)\s*%', html)]
        if pcts and max(pcts) >= 5.0:
            has_contest = ("對抗" in html) and any(
                k in html for k in ("CONFIRMED", "PLAUSIBLE", "REFUTED"))
            if not has_contest:
                hit = max(pcts)
                block(f"【DONE GATE B】偵測到資產單日波動達 ±{hit:.1f}%（≥5%），"
                      "STEP 3.5 要求跑對抗式驗證並在 footer/Section3 交代裁決"
                      "（CONFIRMED/PLAUSIBLE/REFUTED），但報告全文查無對抗裁決字樣。"
                      "請補跑對抗（±5%/政策/持倉任一為是＝開獨立 subagent；皆否才主線程三問）"
                      "並把裁決寫進 footer 後再收工。")
                return
    except Exception:
        pass

    # ---- C. 工具揭露（跑了 or 明標未取得/報錯）----
    try:
        silver_ok = ("signals 工具" in html) or ("silver_daily" in html) \
            or ("本次未取得" in html) or ("本次報錯" in html)
        radar_ok = ("radar-draft" in html) or ("radar 本次" in html) \
            or ("本次未取得" in html) or ("本次報錯" in html)
        if not silver_ok:
            block("【DONE GATE C】6-B 白銀 signals 欄既無工具輸出也無『本次未取得/報錯』揭露"
                  "＝靜默略過。請跑 silver_daily.py 帶入，或明標工具狀態後再收工。")
            return
        if not radar_ok:
            block("【DONE GATE C】6-C/6-D radar 欄既無 radar-draft 也無『本次未取得/報錯』揭露"
                  "＝靜默略過。請跑 radar.py BTC+ETH --html 帶入，或明標工具狀態後再收工。")
            return
    except Exception:
        pass

    # ---- D. STEP 3.8 五標的型態/支撐壓力/多空（標記契約）----
    # 僅在報告已採 <!--3.8:SYM--> 標記契約時作動（出現任一標記才檢查），
    # 舊格式/零標記報告不誤擋；缺任一標的標記且無 :na 揭露 → 擋。
    try:
        found = re.findall(r"<!--3\.8:([A-Z]+)(:na)?-->", html)
        present = {s for s, _na in found}
        if present:
            need = {"XAU", "XAG", "SOXX", "BTC", "MSTR"}
            miss = need - present
            if miss:
                block("【DONE GATE D】STEP 3.8 五標的（XAU/XAG/SOXX/BTC/MSTR）需各報"
                      "『型態+SuperTrend+支撐壓力+多空』並輸出 <!--3.8:SYM--> 標記（工具報錯用"
                      " <!--3.8:SYM:na--> 並貼訊息、SOXX 不得僅標暫缺）。偵測到已採標記契約但缺："
                      + "、".join(sorted(miss)) + "。請補滿後再收工。")
                return
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 任何錯誤都放行，絕不因 hook bug 卡住 Stop
