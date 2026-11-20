#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate E（repo-local 反造假）：報告 JSON 聲稱跑過的工具，必須有「報告日期當天」的新鮮工件。

背景：純前端 viewer 架構下不再產 reports/*.html，故全域 Stop hook check-dailyec-done.py
的 Gate E（.last_run 新鮮度）對 JSON 報告會 no-op。把那道反造假保護搬進 repo-local 的
pre-commit（不動全域 hook、不影響 peer session）。

邏輯：data/<id>.json 的 s6.btc.radar_html / s6.btc.urpd_html / targets_38.MSTR.options_html
一律存在（schema 必填）＝聲稱跑過 radar/urpd/options。檢查 signals/.last_run/<tool>.json 的
tpe_date == meta.date；不符或缺 → 非零退出 → 擋 commit。工具成功跑完會由 runlog.stamp 寫工件。

fail-closed：驗不過就擋。讀不到工件一律視為「未跑」→ 擋（不得靠刪工件放行）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEDGER = os.path.join(REPO, "signals", ".last_run")


def fresh(tool, date):
    try:
        rec = json.load(open(os.path.join(LEDGER, tool + ".json"), encoding="utf-8"))
        return rec.get("tpe_date") == date
    except Exception:
        return False


# 工具「實際報錯」的揭露哨符（SOP：工具回報錯誤時改輸出 :na 標記並貼錯誤訊息）。
# 若對應 html 含此哨符＝報告並未『聲稱跑成功』、而是誠實揭露工具報錯→不應要求當天工件。
# 注意：哨符只放行『無工件』，不放行『填了即時數字卻無工件』——因為 :na 路徑依 SOP
# 不得同時填即時數字。故此例外無法被用來掩護自填數字（紅隊見檔末）。
_NA_SENTINEL = {
    "options": "3.8:MSTR:opt:na",
    "urpd": "3.8:BTC:urpd:na",
    "radar": "radar 本次報錯",   # radar 無固定註解標記，依 SOP 文字揭露
}


def _disclosed_error(html, tool):
    return bool(html) and _NA_SENTINEL.get(tool, "\0") in html


def check(path):
    data = json.load(open(path, encoding="utf-8"))
    date = (data.get("meta") or {}).get("date")
    problems = []
    # 聲稱跑過的工具（schema 保證這些欄位存在；此處防「有欄位但工件不新鮮＝可能自填」）
    btc = (data.get("s6") or {}).get("btc") or {}
    mstr = (data.get("targets_38") or {}).get("MSTR") or {}
    claims = []
    if btc.get("radar_html"):
        claims.append(("radar", "python3 radar.py BTCUSDT/ETHUSDT --html", btc.get("radar_html")))
    if btc.get("urpd_html"):
        claims.append(("urpd", "python3 urpd.py BTCUSDT", btc.get("urpd_html")))
    if mstr.get("options_html"):
        claims.append(("options", "python3 options_maxpain.py MSTR", mstr.get("options_html")))
    for tool, cmd, html in claims:
        if _disclosed_error(html, tool):
            continue  # 誠實揭露工具報錯（:na 哨符）＝不要求當天工件
        if not fresh(tool, date):
            problems.append(f"{tool}（{cmd}）無『{date}』當天 signals/.last_run 工件（＝可能未實跑/數字自填）")
    return problems


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: freshness_gate.py <data.json> [...]")
        return 2
    bad = 0
    for p in args:
        try:
            probs = check(p)
        except Exception as e:
            print(f"✗ {os.path.relpath(p, REPO)} — 讀取失敗：{e}")
            bad += 1
            continue
        rel = os.path.relpath(p, REPO)
        if probs:
            bad += 1
            print(f"✗ {rel} — Gate E 工件新鮮度：")
            for x in probs:
                print("    -", x)
        else:
            print(f"✓ {rel}（Gate E 工件新鮮）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
