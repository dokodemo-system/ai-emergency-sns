"""X だけに1件投稿する（新しい方式 OAuth 2.0 の動作確認用）。Instagram には出さない。

GitHub Actions の x-test-post ワークフローから呼ばれる。本文は環境変数 TEXT で受け取る。
URL を含む本文は publish と同じく止める（課金が高くなるため）。
"""
import os
import sys

import publish
import x_oauth2

if not x_oauth2.enabled():
    sys.exit("X_REFRESH_TOKEN などが未設定です（先に x-oauth2-setup を実行）")
publish.post_x("テスト投稿", {"x_text": os.environ["TEXT"]})
