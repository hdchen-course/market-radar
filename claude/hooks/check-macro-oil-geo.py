#!/usr/bin/env python3
"""Stop hook: dailyecreport 產出「宏觀因果報告」時，強制檢查本回合有沒有查過油價/地緣。

背景：2026-09-01 白銀/黃金/股/債同步大跌，報告只歸因「Fed(Warsh)鷹派+美元強」，
漏了「中東升級→油價漲→通膨恐懼→全球 bond rout」這個共同觸發。skill 本來就有
「跨資產同步暴動＝找共同宏觀觸發、固定抓油價、多管道查地緣」的鐵則，是執行時偷懶漏跑。
這支 hook 當硬性兜底：若本回合寫了 reports/*.html 且內容含「事件級宏觀因果字」，
但整個回合的工具呼叫裡完全沒查過油價、也沒查過地緣/油價新聞 → 阻擋 Stop、要求補查。

設計鐵則（避免誤擋卡死）：
- 只在「明確產了 reports/*.html + 報告含事件級宏觀因果字」時才可能擋；平常橫盤/精簡回覆不擋。
- 「事件級」字刻意選強詞(暴跌/急殺/崩/plunge/risk-off/bond rout/拋售/全面下殺…)，
  避免用普通「跌」字(每份報告都有→會天天誤擋)。
- 任何 exception / 讀不到 transcript / 找不到報告 → 一律放行(exit 0，不 block)。
- 偏「放行」：範圍抓寬(本回合起點抓大)，寧可漏擋也不要亂擋。
"""
import json
import sys
import re

def main():
    raw = sys.stdin.read()
    data = json.loads(raw)
    tp = data.get("transcript_path")
    if not tp:
        return  # 放行
    try:
        with open(tp, encoding="utf-8") as f:
            lines = [json.loads(x) for x in f if x.strip()]
    except Exception:
        return  # 放行

    if not lines:
        return

    # --- 找本回合起點：最後一個「真人 user 輸入」的行 index ---
    # user role 可能帶 tool_result(非真人)；真人輸入的 content 通常是 str 或含 text。
    start = 0
    for i in range(len(lines) - 1, -1, -1):
        ev = lines[i]
        if ev.get("type") == "user":
            msg = ev.get("message", {})
            c = msg.get("content")
            is_human = False
            if isinstance(c, str):
                is_human = True
            elif isinstance(c, list):
                # 含 text 塊且不含 tool_result = 真人
                has_text = any(isinstance(b, dict) and b.get("type") == "text" for b in c)
                has_toolres = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
                is_human = has_text and not has_toolres
            if is_human:
                start = i
                break

    turn = lines[start:]

    # --- 掃本回合：有沒有 Write 一個 reports/*.html，抓其內容 ---
    report_text = ""
    for ev in turn:
        if ev.get("type") != "assistant":
            continue
        for b in ev.get("message", {}).get("content", []):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") in ("Write", "Edit"):
                inp = b.get("input", {})
                fp = inp.get("file_path", "")
                if re.search(r"reports/\d{4}-\d{2}-\d{2}.*\.html", fp):
                    report_text += inp.get("content", "") or inp.get("new_string", "")

    if not report_text:
        return  # 本回合沒產報告 → 放行

    # --- 報告是否含「事件級宏觀因果字」(才需要查油價/地緣) ---
    event_words = ["暴跌", "急殺", "崩", "plunge", "risk-off", "risk off",
                   "bond rout", "拋售", "全面下殺", "全球.{0,4}殺", "插針",
                   "殖利率飆", "全球拋售", "避險回歸", "股災"]
    if not any(re.search(w, report_text, re.I) for w in event_words):
        return  # 非事件級(平常橫盤) → 放行

    # --- 本回合工具呼叫裡有沒有查過油價 / 地緣 ---
    oil_kw = ["CL=F", "BZ=F", "WTI", "Brent", "油價", "crude", "OPEC"]
    # 地緣：CJK 用子字串；拉丁字一律用「詞界」比對，避免 war→Warsh(Fed主席)、oil、Iran→? 等子字串誤判
    geo_cjk = ["伊朗", "中東", "地緣", "戰爭", "關稅", "以色列", "沙烏地",
               "荷莫茲", "胡塞", "制裁", "飛彈", "空襲"]
    geo_latin_re = re.compile(
        r"\b(middle\s*east|geopolit\w*|iran\w*|israel\w*|tariff\w*|warfare|"
        r"air\s*strike|airstrike|sanction\w*|hormuz|houthi|military\s+strike)\b",
        re.I)
    queried_oil = queried_geo = False
    for ev in turn:
        if ev.get("type") != "assistant":
            continue
        for b in ev.get("message", {}).get("content", []):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            blob = json.dumps(b.get("input", {}), ensure_ascii=False)
            if any(k in blob for k in oil_kw):
                queried_oil = True
            if any(k in blob for k in geo_cjk) or geo_latin_re.search(blob):
                queried_geo = True

    if queried_oil or queried_geo:
        return  # 有查過 → 放行

    # --- 命中：產了事件級宏觀報告、卻沒查油價也沒查地緣 → 擋 ---
    reason = ("本回合產出的宏觀因果報告含『事件級跌勢/risk-off/bond rout』字樣，"
              "但整個回合沒有查過油價(CL=F/Brent)也沒查過地緣/油價新聞(中東/OPEC/關稅/戰爭)。"
              "違反 skill 鐵則：跨資產同步大動＝必找共同宏觀觸發、固定抓油價、多管道查地緣。"
              "請先多管道查油價 + 地緣/政策突發(Google News RSS)，確認是否有共同觸發("
              "如中東升級→油價→通膨→bond rout)，據此修正報告的因果歸因後再收工；"
              "若查證後確認無油價/地緣因素，於報告內明寫『已查油價與地緣、無相關催化』即可放行。")
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 任何錯誤都放行，絕不因 hook bug 卡住 Stop
