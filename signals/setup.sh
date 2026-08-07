#!/usr/bin/env bash
# 白銀每日傾向工具 — 自給自足啟動器
# 首次執行:建立 .venv → 裝依賴 → 跑工具
# 之後執行:偵測到 .venv 已就緒就跳過安裝,直接跑工具
#
# 用法:
#   ./setup.sh            # 建置(如需)並執行每日工具
#   ./setup.sh --reinstall  # 強制重建 venv 並重裝依賴
set -euo pipefail

cd "$(dirname "$0")"
VENV=".venv"
PY="$VENV/bin/python"
STAMP="$VENV/.deps_installed"

# --reinstall: 砍掉重來
if [[ "${1:-}" == "--reinstall" ]]; then
  echo "[setup] --reinstall:移除現有 $VENV"
  rm -rf "$VENV"
fi

# 1) 沒有 venv 就建
if [[ ! -x "$PY" ]]; then
  echo "[setup] 建立虛擬環境 $VENV ..."
  python3 -m venv "$VENV"
fi

# 2) 依賴沒裝過、或 requirements.txt 比戳記新 → 裝
if [[ ! -f "$STAMP" || requirements.txt -nt "$STAMP" ]]; then
  echo "[setup] 安裝依賴(requirements.txt)..."
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r requirements.txt
  touch "$STAMP"
  echo "[setup] 依賴就緒。"
else
  echo "[setup] 依賴已就緒,跳過安裝。"
fi

# 3) 跑每日工具
echo "[setup] 執行白銀每日傾向工具 ..."
echo
exec "$PY" silver_daily.py
