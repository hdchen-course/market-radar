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


def check(path):
    data = json.load(open(path, encoding="utf-8"))
    date = (data.get("meta") or {}).get("date")
    problems = []
    # 聲稱跑過的工具（schema 保證這些欄位存在；此處防「有欄位但工件不新鮮＝可能自填」）
    claims = []
    if ((data.get("s6") or {}).get("btc") or {}).get("radar_html"):
        claims.append(("radar", "python3 radar.py BTCUSDT/ETHUSDT --html"))
    if ((data.get("s6") or {}).get("btc") or {}).get("urpd_html"):
        claims.append(("urpd", "python3 urpd.py BTCUSDT"))
    if ((data.get("targets_38") or {}).get("MSTR") or {}).get("options_html"):
        claims.append(("options", "python3 options_maxpain.py MSTR"))
    for tool, cmd in claims:
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
