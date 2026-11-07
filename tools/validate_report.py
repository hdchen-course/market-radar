#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗證一或多個 data/<id>.json 是否符合報告 schema（欄位齊全/型別/最小數量）。

pre-commit hook 會對每個 staged 的 data/*.json 跑這支；任一不合規 → 非零退出 → 擋 commit。
手動用法：
  python3 tools/validate_report.py data/2026-11-07-am.json
  python3 tools/validate_report.py data/*.json
  python3 tools/validate_report.py            # 驗 data/ 下全部
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import report_schema  # noqa: E402


def validate_file(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"JSON 解析失敗：{e}"]
    return report_schema.validate(data)


def main():
    args = sys.argv[1:]
    if not args:
        args = sorted(glob.glob(os.path.join(REPO, "data", "*.json")))
    if not args:
        print("（無 data/*.json 可驗）")
        return 0
    bad = 0
    for p in args:
        errs = validate_file(p)
        rel = os.path.relpath(p, REPO)
        if errs:
            bad += 1
            print(f"✗ {rel} — {len(errs)} 個問題：")
            for e in errs:
                print("    -", e)
        else:
            print(f"✓ {rel}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
