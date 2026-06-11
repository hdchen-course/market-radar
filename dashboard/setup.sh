#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Market Data Dashboard Setup ==="

# Create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for FRED API key
if [ -z "$FRED_API_KEY" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  FRED API Key 設定（免費，一次性）"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  1. 打開: https://fred.stlouisfed.org/docs/api/api_key.html"
    echo "  2. 點 'Request or view your API keys'"
    echo "  3. 用 email 或 Google 登入"
    echo "  4. 複製 32 字元的 API key"
    echo ""
    echo "  取得後，選擇一種方式設定："
    echo ""
    echo "  方法A (每次手動):"
    echo "    export FRED_API_KEY=你的key"
    echo ""
    echo "  方法B (永久寫入 shell，推薦):"
    echo "    echo 'export FRED_API_KEY=你的key' >> ~/.zshrc"
    echo "    source ~/.zshrc"
    echo ""
    echo "  ※ 沒有 FRED key 也能跑，只是少了宏觀數據（殖利率、CPI等）"
    echo "    Yahoo Finance + COT 部分不需要 key。"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "使用方式:"
echo "  source venv/bin/activate"
echo "  python collect.py              # 抓取所有數據 (~30秒)"
echo "  python collect.py --source yf  # 只抓 Yahoo Finance（不需key）"
echo "  python collect.py --source cot # 只抓 COT 持倉數據"
echo "  python render.py --open        # 產生 HTML 並打開"
echo ""
