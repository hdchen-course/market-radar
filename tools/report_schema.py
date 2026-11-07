#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dailyecreport JSON 報告的「單一事實來源」schema + validator。

設計目標（HD 2026-11-07）：報告改成「固定 template 吃一包 JSON」。
- 這支模組定義每份 data/<id>.json 必備的欄位與最小數量。
- tools/validate_report.py（pre-commit hook 用）與 tools/gen_report.py（render）
  都 import 這裡的 SPEC / validate()，確保「驗證」與「產生」對同一份契約，
  缺欄位時 commit 會被 pre-commit hook 擋下 → 保證每份報告格式一致、欄位齊全。

SPEC 語法（宣告式、無裁量）：
  "str"/"num"/"bool"              → 該型別的純量（str 需非空字串）
  ("enum", [a, b, ...])          → 值必須在清單內
  ("opt", inner)                 → 選填；給了就按 inner 驗，沒給不罰
  {...}                          → 物件（dict），逐 key 遞迴
  ("list", min_n, item_spec)     → 陣列，長度 >= min_n，每個元素按 item_spec 驗

本模組零第三方相依（純標準庫），可被 pre-commit hook 直接呼叫。
"""

# STEP 3.8 五標的「四件」契約：型態 / SuperTrend三框 / 支撐壓力(VPVR) / 多空(條件式)
_T38_BASE = {
    "patterns": "str",     # 具名 K 線型態 + 方向 bias
    "supertrend": "str",   # 三框方向 + ATR 數字
    "sr": "str",           # VPVR：POC/VA/HVN/LVN 相對現價的壓力/支撐
    "bias": "str",         # 多空機會：條件式「站上/跌破 X 才偏多/偏空」
}

_SCORECARD = ("list", 1, {"factor": "str", "read": "str", "score": "str"})
_OPS = ("list", 1, {"scenario": "str", "entry": "str", "stop": "str", "target": "str", "rr": "str"})
_SCN5 = ("list", 3, {"name": "str", "prob": "str", "desc": "str"})

_TACTICAL = {
    "st": "str",                 # SuperTrend 三框帶 ATR 數字
    "scorecard": _SCORECARD,     # 計分卡
    "bias_24h": "str",           # 24h 預估（ATR 公式）
    "ops": _OPS,                 # 操作 table（含風報比 rr）
    "scenarios_5d": _SCN5,       # 5 日情境
    "extra": "str",              # 傳導/籌碼/屬性/衍生品 等補充
}

SPEC = {
    "meta": {
        "date": "str",                       # YYYY-MM-DD
        "type": ("enum", ["am", "pm"]),
        "version": "str",
        "theme": "str",                      # header 一句話主題
        "regime": {
            "label": "str",
            "color": ("enum", ["green", "accent", "bear", "tail", "yellow", "purple", "cyan"]),
        },
        "generated_tpe": "str",              # 產生時台北時戳
        "us_session": "str",                 # 對應美股盤別/收盤日
    },

    "s0_backtest": {
        "prev": "str",
        "hit_summary": "str",
        "rows": ("list", 1, {
            "sym": "str", "pred_range": "str", "pred_dir": "str",
            "actual": "str", "result": "str",
        }),
        "lesson": "str",
    },

    "s1_quotes": {
        "assets": ("list", 22, {
            "sym": "str", "name": "str", "price": "str",
            "chg": "str", "dir": ("enum", ["up", "down", "flat"]),
        }),
        "macro": {
            "dxy": "str", "vix": "str", "us10y": "str", "us30y": "str",
            "hy_oas": "str", "ig_oas": "str", "taiex": "str",
            "usdjpy": "str", "fng": "str",
            "move": ("opt", "str"), "jp10y": ("opt", "str"), "de10y": ("opt", "str"),
        },
    },

    "s2_regime": {
        "rows": ("list", 5, {"dim": "str", "content": "str"}),
    },

    "s3_consensus": {
        "rows": ("list", 1, {"theme": "str", "expect": "str", "actual": "str", "mispricing": "str"}),
        "alert": "str",
    },

    "s4_matrix": {
        "rows": ("list", 15, {
            "rank": "str", "asset": "str", "chg": "str", "st": "str",
            "driver": "str", "leg_tag": ("opt", "str"),
        }),
    },

    "s5_risk": {
        "risks": ("list", 4, {
            "risk": "str", "prob": "str", "impact": "str",
            "assets": "str", "severity": "num",
        }),
        "setups": ("list", 12, {"asset": "str", "price": "str", "pattern": "str", "basis": "str"}),
    },

    "s6": {
        "xau": _TACTICAL,
        "xag": dict(_TACTICAL, signals_box="str"),   # 白銀多一個 signals 工具參考欄
        "btc": dict(_TACTICAL, radar_html="str", urpd_html="str"),
        "eth": dict(_TACTICAL, radar_html="str"),
        "stocks": {
            "gainers": ("list", 3, {"sym": "str", "chg": "str", "analysis": "str"}),
            "losers": ("list", 3, {"sym": "str", "chg": "str", "analysis": "str"}),
            "quick": ("list", 1, {
                "sym": "str", "price": "str", "chg": "str",
                "dir": "str", "levels": "str", "note": "str",
            }),
        },
    },

    "s7_banks": {
        "rows": ("list", 1, {"src": "str", "view": "str", "impact": "str"}),
        "options_structure": "str",
    },

    "s8_calendar": {
        "events": ("list", 5, {"date": "str", "event": "str"}),
        "ranking": "str",
    },

    "s9_scenarios": {
        "prediction_market": ("list", 1, {"item": "str", "prob": "str", "note": "str"}),
        "base": {"prob": "str", "desc": "str"},
        "bull": {"prob": "str", "desc": "str"},
        "bear": {"prob": "str", "desc": "str"},
        "tail": {"prob": "str", "desc": "str"},
    },

    # STEP 3.8 五標的四件（gen 會據此輸出 <!--3.8:SYM--> 標記）
    "targets_38": {
        "XAU": _T38_BASE,
        "XAG": _T38_BASE,
        "SOXX": _T38_BASE,
        "BTC": dict(_T38_BASE, urpd_html="str"),       # 另附 URPD（<!--3.8:BTC:urpd-->）
        "MSTR": dict(_T38_BASE, options_html="str"),   # 另附選擇權（<!--3.8:MSTR:opt-->）
    },

    # STEP 3.5 對抗式裁決（footer 必含；gate 任一為真＝必開 subagent）
    "adversarial": {
        "gate_a": "bool",
        "gate_b": "bool",
        "gate_c": "bool",
        "subagent_opened": "bool",
        "verdicts": ("list", 1, {
            "claim": "str",
            "verdict": ("enum", ["CONFIRMED", "PLAUSIBLE", "REFUTED"]),
            "note": "str",
        }),
    },

    # 開盤前戰略定調儀表板（資料由 signals/strategic_dashboard.py 的 dashboard_payload() 共用函式產生）
    "dashboard": {
        "summary": "str",
        "generated": "str",
        "riskoff": {"score": "str", "label": "str", "stress": "bool", "data_bad": "bool"},
        "intraday": {"single": "str", "chop": "str", "label": "str"},
        "breadth": {"text": "str", "up": "num", "dn": "num", "nn": "num"},
        "risk_rows": ("list", 1, {"lbl": "str", "val": "str0", "chg": "str0"}),
        "trend_rows": ("list", 1, {"lbl": "str", "val": "str0", "chg": "str0"}),
        "etf": ("list", 1, {"grp": "str", "long": "str", "mult": "str", "long_chg": "str0",
                            "short": "str", "short_chg": "str0", "rvol": "str0"}),
        "lights": ("list", 1, {"name": "str", "signal": "str", "tok": "str", "why": "str0"}),
        "binance": ("list", 1, {"name": "str", "price": "str0", "chg": "str0"}),
        "movers_up": ("list", 0, {"sym": "str", "pct": "str", "px": "str"}),
        "movers_dn": ("list", 0, {"sym": "str", "pct": "str", "px": "str"}),
    },

    "footer": "str",
}


def _tname(spec):
    if isinstance(spec, dict):
        return "object"
    if isinstance(spec, tuple):
        return spec[0]
    return spec


def _check(value, spec, path, errs):
    # ("opt", inner)：None/缺 → 跳過；否則按 inner
    if isinstance(spec, tuple) and spec[0] == "opt":
        if value is None:
            return
        _check(value, spec[1], path, errs)
        return

    if isinstance(spec, dict):
        if not isinstance(value, dict):
            errs.append(f"{path}: 需為 object，實得 {type(value).__name__}")
            return
        for k, sub in spec.items():
            if k not in value or value[k] is None:
                # 選填不罰
                if isinstance(sub, tuple) and sub[0] == "opt":
                    continue
                errs.append(f"{path}.{k}: 缺少必填欄位")
                continue
            _check(value[k], sub, f"{path}.{k}", errs)
        return

    if isinstance(spec, tuple) and spec[0] == "enum":
        if value not in spec[1]:
            errs.append(f"{path}: 值 {value!r} 不在允許清單 {spec[1]}")
        return

    if isinstance(spec, tuple) and spec[0] == "list":
        _, min_n, item = spec
        if not isinstance(value, list):
            errs.append(f"{path}: 需為 list，實得 {type(value).__name__}")
            return
        if len(value) < min_n:
            errs.append(f"{path}: 需至少 {min_n} 個元素，實得 {len(value)}")
        for i, el in enumerate(value):
            _check(el, item, f"{path}[{i}]", errs)
        return

    # 純量
    if spec == "str":
        if not isinstance(value, str) or not value.strip():
            errs.append(f"{path}: 需為非空字串")
    elif spec == "str0":   # 允許空字串（如儀表板某些 val/chg 欄可為空）
        if not isinstance(value, str):
            errs.append(f"{path}: 需為字串")
    elif spec == "num":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errs.append(f"{path}: 需為數字")
    elif spec == "bool":
        if not isinstance(value, bool):
            errs.append(f"{path}: 需為布林值")
    else:
        errs.append(f"{path}: 未知 spec {spec!r}")


def validate(data):
    """回傳錯誤訊息清單；空清單＝通過。"""
    errs = []
    if not isinstance(data, dict):
        return ["根節點需為 object"]
    for k, spec in SPEC.items():
        if k not in data or data[k] is None:
            errs.append(f"{k}: 缺少必填頂層區塊")
            continue
        _check(data[k], spec, k, errs)
    # 跨欄位一致性檢查
    adv = data.get("adversarial") or {}
    if isinstance(adv, dict):
        if (adv.get("gate_a") or adv.get("gate_b") or adv.get("gate_c")) and not adv.get("subagent_opened"):
            errs.append("adversarial: 任一 gate 為真時 subagent_opened 必須為 true（需開獨立對抗 subagent）")
    return errs


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: report_schema.py <data.json>")
        sys.exit(2)
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    e = validate(d)
    if e:
        print("INVALID:")
        for x in e:
            print("  -", x)
        sys.exit(1)
    print("VALID")
