#!/usr/bin/env bash
# クラウド実行環境の準備（毎回の定期実行の最初に実行。入っていれば即終了）
set -e
python3 -c "import playwright, PIL" 2>/dev/null || pip install -q playwright pillow
python3 - <<'PY' 2>/dev/null || python3 -m playwright install --with-deps chromium
from playwright.sync_api import sync_playwright
with sync_playwright() as p: p.chromium.launch().close()
PY
fc-list | grep -qi "Noto Sans CJK" || (sudo apt-get update -qq && sudo apt-get install -y -qq fonts-noto-cjk) || (apt-get update -qq && apt-get install -y -qq fonts-noto-cjk)
command -v ffmpeg >/dev/null || (sudo apt-get install -y -qq ffmpeg) || (apt-get install -y -qq ffmpeg)
echo "setup ok"
