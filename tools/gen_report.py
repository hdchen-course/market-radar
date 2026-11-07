#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""固定 template 產生器：data/<id>.json → reports/<id>.html（+ 可選 append reports.json）。

HD 2026-11-07 架構：報告內容只維護在 data/<id>.json（單一事實來源）；本產生器用
「固定 template」把它 render 成與既有報告庫同房屋風格的靜態 HTML，落在 reports/，
index.html 的行事曆/連結零改動即可顯示。pre-commit hook 會先 validate 再呼叫本檔。

保證（讓既有 DONE-GATE Stop hook 完全相容）：
  - 輸出五標的 <!--3.8:XAU/XAG/SOXX/BTC/MSTR--> 標記 + <!--3.8:MSTR:opt--> + <!--3.8:BTC:urpd-->
  - 報價面板用 class="ch pos|neg" 帶 % → hook B 的 ±5% 偵測可運作
  - 對抗裁決段含「對抗」+ CONFIRMED/PLAUSIBLE/REFUTED
  - radar_html 內含 radar-draft；白銀 signals_box 含「signals 工具」

用法：
  python3 tools/gen_report.py data/2026-11-07-am.json            # 只產 HTML
  python3 tools/gen_report.py data/2026-11-07-am.json --append   # 並 append reports.json
"""
import json
import os
import sys
import html as _html

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import report_schema  # noqa: E402

HOUSE_CSS = (
    "<style>:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#e6edf3;"
    "--muted:#8b949e;--accent:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922;"
    "--orange:#db6d28;--purple:#a371f7;--cyan:#39d5ff}*{margin:0;padding:0;box-sizing:border-box}"
    "body{font-family:-apple-system,BlinkMacSystemFont,'Noto Sans TC',sans-serif;background:var(--bg);"
    "color:var(--text);line-height:1.7;padding:20px}.container{max-width:1440px;margin:0 auto}"
    "header{text-align:center;padding:28px 0;border-bottom:1px solid var(--border);margin-bottom:28px}"
    "header h1{font-size:1.4rem;margin-bottom:6px;letter-spacing:1px}header .sub{color:var(--muted);font-size:.85rem}"
    ".badge{display:inline-block;padding:5px 14px;border-radius:20px;font-weight:600;font-size:.8rem;margin-top:10px}"
    ".badge-green{background:linear-gradient(135deg,#238636,#3fb950)}"
    ".badge-warn{background:linear-gradient(135deg,#db6d28,#f85149)}"
    ".card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:22px}"
    ".card h2{font-size:.98rem;margin-bottom:12px;color:var(--accent)}.full{grid-column:1/-1}"
    "table{width:100%;border-collapse:collapse;font-size:.8rem}th,td{padding:6px 8px;text-align:left;"
    "border-bottom:1px solid var(--border)}th{color:var(--muted);font-weight:500;font-size:.74rem}"
    ".pos{color:var(--green)}.neg{color:var(--red)}.neu{color:var(--yellow)}.warn{color:var(--orange)}"
    ".tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.7rem;font-weight:600}"
    ".t-bull{background:rgba(63,185,80,.15);color:var(--green)}.t-bear{background:rgba(248,81,73,.15);color:var(--red)}"
    ".t-neu{background:rgba(210,153,34,.15);color:var(--yellow)}.t-hold{background:rgba(88,166,255,.15);color:var(--accent)}"
    ".mr{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border)}"
    ".mr:last-child{border-bottom:none}.mr-l{color:var(--muted);font-size:.8rem}.mr-v{font-weight:600;font-size:.85rem}"
    ".price-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:7px}"
    ".pi{background:rgba(255,255,255,.03);border-radius:7px;padding:9px 11px}"
    ".pi .tk{font-size:.72rem;color:var(--muted);margin-bottom:1px}.pi .pr{font-size:.95rem;font-weight:700}"
    ".pi .ch{font-size:.75rem;margin-top:1px}"
    ".risk-bar{height:5px;border-radius:3px;background:var(--border);display:inline-block;width:55px;vertical-align:middle;overflow:hidden}"
    ".risk-bar .f{height:100%;border-radius:3px}.rh .f{background:var(--red);width:90%}.rm .f{background:var(--orange);width:60%}"
    ".rl .f{background:var(--green);width:30%}.rmh .f{background:var(--orange);width:75%}"
    ".tl{position:relative;padding-left:22px}.tl::before{content:'';position:absolute;left:7px;top:0;bottom:0;width:2px;background:var(--border)}"
    ".tl-i{position:relative;margin-bottom:13px}.tl-i::before{content:'';position:absolute;left:-18px;top:7px;width:9px;height:9px;border-radius:50%;background:var(--accent)}"
    ".tl-d{font-size:.76rem;color:var(--accent);font-weight:600}.tl-e{font-size:.8rem;margin-top:2px}"
    ".scenario{border-left:3px solid var(--green);padding:10px;margin:8px 0}"
    ".scenario-bear{border-left:3px solid var(--red);padding:10px;margin:8px 0}"
    ".scenario-tail{border-left:3px solid var(--orange);padding:10px;margin:8px 0}"
    ".tactical-box{background:rgba(88,166,255,.04);border:1px solid rgba(88,166,255,.2);border-radius:8px;padding:14px;margin:10px 0}"
    ".tool-box{background:rgba(163,113,247,.06);border:1px dashed rgba(163,113,247,.4);border-radius:8px;padding:12px;margin:10px 0}"
    ".tool-box h4{color:var(--purple);font-size:.85rem;margin-bottom:6px}"
    ".radar-draft{background:rgba(57,213,255,.05);border:1px solid rgba(57,213,255,.3);border-radius:8px;padding:12px;margin:10px 0;font-size:.78rem}"
    ".radar-head{color:var(--cyan);font-weight:700;margin-bottom:8px}.radar-panel td{font-size:.76rem}"
    ".radar-bull{color:var(--green);margin-top:6px}.radar-bear{color:var(--red);margin-top:6px}.radar-watch{color:var(--muted);margin-top:6px}"
    ".radar-draft ul{margin:4px 0 4px 18px}.radar-note{color:var(--muted);font-size:.7rem;margin-top:8px;opacity:.8}"
    ".score-card{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.score-item{padding:3px 8px;border-radius:4px;font-size:.72rem;font-weight:600}"
    ".sc-pass{background:rgba(63,185,80,.12);color:var(--green)}.sc-fail{background:rgba(248,81,73,.12);color:var(--red)}"
    ".sc-neutral{background:rgba(210,153,34,.12);color:var(--yellow)}"
    ".st-summary{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}.st-tag{padding:3px 9px;border-radius:4px;font-size:.72rem;font-weight:700}"
    ".scenario-prob{font-size:.72rem;padding:2px 6px;border-radius:3px;background:rgba(88,166,255,.12);color:var(--accent);font-weight:700}"
    ".footer{opacity:.85;font-size:.74rem;color:var(--muted);margin-top:22px;padding:14px;border-top:1px solid var(--border)}"
    ".alert{background:#0a1a0a;border:1px solid #238636;border-radius:6px;padding:12px;margin:8px 0}"
    ".alert-warn{background:#1a1000;border:1px solid#db6d28;border-radius:6px;padding:12px;margin:8px 0}"
    ".opt-box{background:rgba(219,109,40,.06);border:1px solid rgba(219,109,40,.35);border-radius:8px;padding:12px;margin:10px 0;font-size:.78rem}"
    ".urpd-box{background:rgba(210,153,34,.06);border:1px solid rgba(210,153,34,.35);border-radius:8px;padding:12px;margin:10px 0;font-size:.78rem}"
    ".vpvr-box{background:rgba(88,166,255,.05);border:1px solid rgba(88,166,255,.25);border-radius:8px;padding:10px;margin:8px 0;font-size:.77rem}"
    ".t38{background:rgba(63,185,80,.04);border:1px solid rgba(63,185,80,.22);border-radius:8px;padding:12px;margin:10px 0}"
    ".t38 h4{color:var(--green);font-size:.86rem;margin-bottom:6px}.t38 .row{font-size:.78rem;margin:3px 0}"
    ".t38 .k{color:var(--muted);display:inline-block;min-width:72px}"
    "</style>"
)


def esc(s):
    return _html.escape(str(s if s is not None else ""))


def chcls(d):
    return {"up": "pos", "down": "neg"}.get(d, "neu")


def sign_cls(chg):
    c = str(chg).strip()
    if c.startswith("-"):
        return "neg"
    if c.startswith("+"):
        return "pos"
    return "neu"


def _sc_cls(score):
    s = str(score)
    if any(k in s for k in ("多", "bull", "✅", "利多", "偏多")):
        return "sc-pass"
    if any(k in s for k in ("空", "bear", "❌", "利空", "偏空")):
        return "sc-fail"
    return "sc-neutral"


def render(data):
    m = data["meta"]
    badge_cls = "badge-green" if m["regime"]["color"] in ("green", "accent", "cyan") else "badge-warn"
    out = []
    A = out.append

    A("<!DOCTYPE html>")
    A('<html lang="zh-TW"><head><meta charset="UTF-8">')
    A('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    A(f"<title>Market Radar {esc(m['date'])}-{esc(m['type'])}</title>")
    A(HOUSE_CSS)
    A("</head><body><div class=\"container\">")

    # header
    A("<header>")
    A("<h1>終極宏觀流動性 &amp; AI Capex 量化籌碼雷達 V4.5</h1>")
    A(f"<p class=\"sub\">{esc(m['date'])}（{esc(m['type']).upper()}）｜{esc(m['generated_tpe'])}｜{esc(m['us_session'])}</p>")
    A(f"<div class=\"badge {badge_cls}\">{esc(m['regime']['label'])}</div>")
    A("</header>")

    # S0
    s0 = data["s0_backtest"]
    A('<div class="card full"><h2>0. 上期預測回顧（' + esc(s0["prev"]) + "）</h2>")
    A(f"<p style='font-size:.82rem;margin-bottom:8px'>{esc(s0['hit_summary'])}</p>")
    A("<table><tr><th>標的</th><th>預測區間</th><th>方向</th><th>實際</th><th>結果</th></tr>")
    for r in s0["rows"]:
        A(f"<tr><td>{esc(r['sym'])}</td><td>{esc(r['pred_range'])}</td><td>{esc(r['pred_dir'])}</td>"
          f"<td>{esc(r['actual'])}</td><td>{esc(r['result'])}</td></tr>")
    A("</table>")
    A(f"<div class='alert' style='margin-top:10px'>📘 教訓：{esc(s0['lesson'])}</div></div>")

    # S1
    s1 = data["s1_quotes"]
    A('<div class="card full"><h2>1. 即時報價面板</h2><div class="price-grid">')
    for a in s1["assets"]:
        A(f"<div class='pi'><div class='tk'>{esc(a['sym'])} {esc(a['name'])}</div>"
          f"<div class='pr'>{esc(a['price'])}</div>"
          f'<div class="ch {chcls(a["dir"])}">{esc(a["chg"])}</div></div>')
    A("</div>")
    mc = s1["macro"]
    order = [("DXY", "dxy"), ("VIX", "vix"), ("MOVE", "move"), ("美10Y", "us10y"), ("美30Y", "us30y"),
             ("日10Y", "jp10y"), ("德10Y", "de10y"), ("HY利差", "hy_oas"), ("IG利差", "ig_oas"),
             ("TAIEX", "taiex"), ("USD/JPY", "usdjpy"), ("F&G", "fng")]
    A("<div style='margin-top:10px'>")
    for label, k in order:
        if mc.get(k):
            A(f"<span class='tag t-hold' style='margin:2px'>{esc(label)} {esc(mc[k])}</span>")
    A("</div></div>")

    # S2
    A('<div class="card full"><h2>2. 市場主導 Regime</h2>')
    for r in data["s2_regime"]["rows"]:
        A(f"<div class='mr'><span class='mr-l'>{esc(r['dim'])}</span><span class='mr-v'>{esc(r['content'])}</span></div>")
    A("</div>")

    # S3
    s3 = data["s3_consensus"]
    A('<div class="card full"><h2>3. 市場共識 vs Reality</h2>')
    A("<table><tr><th>主題</th><th>預期</th><th>實際</th><th>Mispricing</th></tr>")
    for r in s3["rows"]:
        A(f"<tr><td>{esc(r['theme'])}</td><td>{esc(r['expect'])}</td><td>{esc(r['actual'])}</td><td>{esc(r['mispricing'])}</td></tr>")
    A("</table>")
    A(f"<div class='alert-warn' style='margin-top:10px'>⚠ 最大 Mispricing：{esc(s3['alert'])}</div></div>")

    # S4
    A('<div class="card full"><h2>4. 跨資產強弱矩陣</h2>')
    A("<table><tr><th>#</th><th>資產</th><th>24h%</th><th>ST方向</th><th>驅動</th></tr>")
    for r in data["s4_matrix"]["rows"]:
        leg = f" <span class='tag t-neu'>{esc(r['leg_tag'])}</span>" if r.get("leg_tag") else ""
        A(f"<tr><td>{esc(r['rank'])}</td><td>{esc(r['asset'])}</td>"
          f'<td class="{sign_cls(r["chg"])}">{esc(r["chg"])}</td><td>{esc(r["st"])}</td>'
          f"<td>{esc(r['driver'])}{leg}</td></tr>")
    A("</table></div>")

    # S5
    s5 = data["s5_risk"]
    A('<div class="card full"><h2>5. 量化風險雷達</h2>')
    A("<table><tr><th>風險</th><th>機率</th><th>影響</th><th>資產</th><th>嚴重度</th></tr>")
    sevcls = {5: "rh", 4: "rmh", 3: "rm", 2: "rl", 1: "rl"}
    for r in s5["risks"]:
        sc = sevcls.get(int(r["severity"]), "rm")
        A(f"<tr><td>{esc(r['risk'])}</td><td>{esc(r['prob'])}</td><td>{esc(r['impact'])}</td>"
          f"<td>{esc(r['assets'])}</td><td><span class='risk-bar {sc}'><span class='f'></span></span></td></tr>")
    A("</table>")
    A("<table style='margin-top:10px'><tr><th>資產</th><th>現價</th><th>型態</th><th>依據</th></tr>")
    for r in s5["setups"]:
        A(f"<tr><td>{esc(r['asset'])}</td><td>{esc(r['price'])}</td><td>{esc(r['pattern'])}</td><td>{esc(r['basis'])}</td></tr>")
    A("</table></div>")

    # S6
    A('<div class="card full"><h2>6. 完整戰術分析</h2>')
    s6 = data["s6"]
    titles = {"xau": "A. 黃金 XAU", "xag": "B. 白銀 XAG", "btc": "C. 比特幣 BTC", "eth": "D. 以太坊 ETH"}
    for key in ("xau", "xag", "btc", "eth"):
        t = s6[key]
        A(f"<div class='tactical-box'><h4 style='color:var(--accent);margin-bottom:6px'>{titles[key]}</h4>")
        A(f"<div class='st-summary'><span class='st-tag t-hold'>SuperTrend：{esc(t['st'])}</span></div>")
        A("<div class='score-card'>")
        for sc in t["scorecard"]:
            A(f"<span class='score-item {_sc_cls(sc['score'])}'>{esc(sc['factor'])}：{esc(sc['read'])}（{esc(sc['score'])}）</span>")
        A("</div>")
        A(f"<p style='font-size:.8rem;margin:6px 0'><b>24h 預估：</b>{esc(t['bias_24h'])}</p>")
        A("<table><tr><th>情境</th><th>進場</th><th>止損</th><th>目標</th><th>風報比</th></tr>")
        for o in t["ops"]:
            A(f"<tr><td>{esc(o['scenario'])}</td><td>{esc(o['entry'])}</td><td>{esc(o['stop'])}</td>"
              f"<td>{esc(o['target'])}</td><td>{esc(o['rr'])}</td></tr>")
        A("</table>")
        A("<table style='margin-top:8px'><tr><th>5日情境</th><th>機率</th><th>說明</th></tr>")
        for s in t["scenarios_5d"]:
            A(f"<tr><td>{esc(s['name'])}</td><td>{esc(s['prob'])}</td><td>{esc(s['desc'])}</td></tr>")
        A("</table>")
        A(f"<p style='font-size:.8rem;margin-top:6px'>{esc(t['extra'])}</p>")
        if key == "xag" and t.get("signals_box"):
            A("<div class='tool-box'><h4>🔧 signals 工具參考欄（實驗性、非進場依據）</h4>"
              f"<div style='font-size:.77rem'>{t['signals_box']}</div></div>")
        if key in ("btc", "eth") and t.get("radar_html"):
            A(t["radar_html"])
        if key == "btc" and t.get("urpd_html"):
            A(t["urpd_html"])
        A("</div>")

    # 6-E stocks
    st = s6["stocks"]
    A("<div class='tactical-box'><h4 style='color:var(--accent)'>E. 美股焦點</h4>")
    A("<p style='font-size:.8rem;margin:4px 0'><b>🔺 漲幅前段</b></p><table><tr><th>標的</th><th>24h%</th><th>分析</th></tr>")
    for g in st["gainers"]:
        A(f"<tr><td>{esc(g['sym'])}</td><td class='{sign_cls(g['chg'])}'>{esc(g['chg'])}</td><td>{esc(g['analysis'])}</td></tr>")
    A("</table>")
    A("<p style='font-size:.8rem;margin:8px 0 4px'><b>🔻 跌幅/弱勢</b></p><table><tr><th>標的</th><th>24h%</th><th>分析</th></tr>")
    for g in st["losers"]:
        A(f"<tr><td>{esc(g['sym'])}</td><td class='{sign_cls(g['chg'])}'>{esc(g['chg'])}</td><td>{esc(g['analysis'])}</td></tr>")
    A("</table>")
    A("<p style='font-size:.8rem;margin:8px 0 4px'><b>其餘快評</b></p><table><tr><th>標的</th><th>價格</th><th>24h%</th><th>方向</th><th>關鍵價位</th><th>備註</th></tr>")
    for q in st["quick"]:
        A(f"<tr><td>{esc(q['sym'])}</td><td>{esc(q['price'])}</td><td class='{sign_cls(q['chg'])}'>{esc(q['chg'])}</td>"
          f"<td>{esc(q['dir'])}</td><td>{esc(q['levels'])}</td><td>{esc(q['note'])}</td></tr>")
    A("</table></div>")

    # 6-F MSTR options
    mstr = data["targets_38"]["MSTR"]
    A("<div class='tactical-box'><h4 style='color:var(--accent)'>F. MSTR 選擇權籌碼（結構底稿，非進場訊號）</h4>")
    A(mstr["options_html"])
    A("</div>")
    A("</div>")  # end S6

    # STEP 3.8 五標的四件（含標記）
    A('<div class="card full"><h2>★ STEP 3.8 五標的型態 / 支撐壓力 / 多空</h2>')
    t38 = data["targets_38"]
    names = {"XAU": "黃金 XAU", "XAG": "白銀 XAG", "SOXX": "半導體 SOXX", "BTC": "比特幣 BTC", "MSTR": "MSTR"}
    for sym in ("XAU", "XAG", "SOXX", "BTC", "MSTR"):
        g = t38[sym]
        A(f"<!--3.8:{sym}-->")
        A(f"<div class='t38'><h4>{names[sym]}</h4>")
        A(f"<div class='row'><span class='k'>型態</span>{esc(g['patterns'])}</div>")
        A(f"<div class='row'><span class='k'>SuperTrend</span>{esc(g['supertrend'])}</div>")
        A(f"<div class='row'><span class='k'>支撐壓力</span>{esc(g['sr'])}</div>")
        A(f"<div class='row'><span class='k'>多空機會</span>{esc(g['bias'])}</div>")
        if sym == "BTC":
            A("<!--3.8:BTC:urpd-->")
            A(g["urpd_html"])
        if sym == "MSTR":
            A("<!--3.8:MSTR:opt-->")
            A(g["options_html"])
        A("</div>")
    A("</div>")

    # S7
    s7 = data["s7_banks"]
    A('<div class="card full"><h2>7. 投行觀點與期權結構異常</h2>')
    A("<table><tr><th>來源</th><th>觀點</th><th>影響</th></tr>")
    for r in s7["rows"]:
        A(f"<tr><td>{esc(r['src'])}</td><td>{esc(r['view'])}</td><td>{esc(r['impact'])}</td></tr>")
    A("</table>")
    A(f"<p style='font-size:.8rem;margin-top:8px'>{esc(s7['options_structure'])}</p></div>")

    # S8
    s8 = data["s8_calendar"]
    A('<div class="card full"><h2>8. 一週核心事件 Calendar（台灣時間）</h2><div class="tl">')
    for e in s8["events"]:
        A(f"<div class='tl-i'><div class='tl-d'>{esc(e['date'])}</div><div class='tl-e'>{esc(e['event'])}</div></div>")
    A("</div>")
    A(f"<p style='font-size:.8rem;margin-top:8px'>{esc(s8['ranking'])}</p></div>")

    # S9
    s9 = data["s9_scenarios"]
    A('<div class="card full"><h2>9. 一週情境劇本與機率評估</h2>')
    A("<table><tr><th>預測市場</th><th>機率</th><th>備註</th></tr>")
    for r in s9["prediction_market"]:
        A(f"<tr><td>{esc(r['item'])}</td><td>{esc(r['prob'])}</td><td>{esc(r['note'])}</td></tr>")
    A("</table>")
    for key, cls, label in (("base", "scenario", "Base Case"), ("bull", "scenario", "Bull Case"),
                            ("bear", "scenario-bear", "Bear Case"), ("tail", "scenario-tail", "Tail Risk")):
        sc = s9[key]
        A(f"<div class='{cls}'><span class='scenario-prob'>{label} · {esc(sc['prob'])}</span>"
          f"<p style='font-size:.82rem;margin-top:4px'>{esc(sc['desc'])}</p></div>")
    A("</div>")

    # 對抗裁決 footer
    adv = data["adversarial"]
    A('<div class="card full"><h2>🔴 STEP 3.5 對抗式驗證裁決</h2>')
    A(f"<p style='font-size:.8rem'>閘門：(a) ±5% = <b>{'是' if adv['gate_a'] else '否'}</b>｜"
      f"(b) 政策/數據事件 = <b>{'是' if adv['gate_b'] else '否'}</b>｜"
      f"(c) 持倉動作 = <b>{'是' if adv['gate_c'] else '否'}</b>｜"
      f"獨立 subagent = <b>{'已開' if adv['subagent_opened'] else '未開'}</b></p>")
    A("<table style='margin-top:8px'><tr><th>因果宣稱</th><th>裁決</th><th>說明</th></tr>")
    vcls = {"CONFIRMED": "pos", "PLAUSIBLE": "neu", "REFUTED": "neg"}
    for v in adv["verdicts"]:
        A(f"<tr><td>{esc(v['claim'])}</td><td class='{vcls.get(v['verdict'], 'neu')}'>{esc(v['verdict'])}</td>"
          f"<td>{esc(v['note'])}</td></tr>")
    A("</table></div>")

    A(f"<div class='footer'>{esc(data['footer'])}</div>")
    A("</div></body></html>")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("usage: gen_report.py <data.json> [--append]")
        sys.exit(2)
    path = sys.argv[1]
    data = json.load(open(path, encoding="utf-8"))
    errs = report_schema.validate(data)
    if errs:
        print("REFUSE: data 未通過 schema，請先補齊欄位：", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        sys.exit(1)
    m = data["meta"]
    rid = f"{m['date']}-{m['type']}"
    html_out = render(data)
    outpath = os.path.join(REPO, "reports", rid + ".html")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(html_out)
    print("WROTE", os.path.relpath(outpath, REPO), f"({len(html_out)} bytes)")

    if "--append" in sys.argv:
        rjpath = os.path.join(REPO, "reports.json")
        rj = json.load(open(rjpath, encoding="utf-8"))
        entry = {"date": m["date"], "type": m["type"], "file": rid + ".html"}
        if not any(e.get("date") == m["date"] and e.get("type") == m["type"] for e in rj):
            rj.append(entry)
            with open(rjpath, "w", encoding="utf-8") as f:
                json.dump(rj, f, ensure_ascii=False, indent=1)
            print("APPENDED reports.json", entry)
        else:
            print("reports.json already has", rid)


if __name__ == "__main__":
    main()
