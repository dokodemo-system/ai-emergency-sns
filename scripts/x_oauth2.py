"""X の OAuth 2.0（ユーザー認証）のトークンを扱う。

X は OAuth 1.0a を 2027-01-31 で終了するため、OAuth 2.0 に切り替える。
  - 最初の1回だけ：今の OAuth 1.0a のキーを OAuth 2.0 のトークンに交換する（setup）
  - 毎回：リフレッシュトークンで新しいアクセストークン（2時間有効）をもらう
  - リフレッシュトークンは使い捨てなので、もらった新しい値を GitHub Secrets（X_REFRESH_TOKEN）に書き戻す

キー類は GitHub Secrets から環境変数で渡される（Claude には渡らない）。

使い方（GitHub Actions の x-oauth2-setup ワークフローから）:
  python scripts/x_oauth2.py setup
"""
import os
import subprocess
import sys

import requests

TOKEN_URL = "https://api.x.com/2/oauth2/token"
REPO = os.environ.get("GITHUB_REPOSITORY", "dokodemo-system/ai-emergency-sns")
_cache = {}


def _client():
    return os.environ["X_CLIENT_ID"], os.environ["X_CLIENT_SECRET"]


class TokenError(RuntimeError):
    def __init__(self, status, text):
        super().__init__(f"X トークン取得エラー {status}: {text}")
        self.status = status


def _token_request(data):
    # サーバー用（confidential）アプリなので、Client ID:Secret を Basic 認証で送る（本文に client_id は入れない）
    r = requests.post(TOKEN_URL, data=data, auth=_client(), timeout=60)
    if r.status_code >= 400:
        raise TokenError(r.status_code, r.text)
    tok = r.json()
    for k in ("access_token", "refresh_token"):
        if tok.get(k):
            print(f"::add-mask::{tok[k]}")  # 念のためログに出ても伏せ字にする
    if not tok.get("refresh_token"):
        raise RuntimeError("X からリフレッシュトークンが返りませんでした")
    return tok


def save_refresh_token(token):
    """新しいリフレッシュトークンを GitHub Secrets に書き戻す（値は標準入力で渡し、画面やログに出さない）。"""
    pat = os.environ.get("SECRETS_PAT")
    if not pat:
        raise RuntimeError("SECRETS_PAT が未設定のため、新しいリフレッシュトークンを保存できません")
    subprocess.run(["gh", "secret", "set", "X_REFRESH_TOKEN", "--repo", REPO],
                   input=token, text=True, check=True, env={**os.environ, "GH_TOKEN": pat},
                   stdout=subprocess.DEVNULL)


def exchange_oauth1():
    """今の OAuth 1.0a のキーを OAuth 2.0 のトークンに交換する（2027-01-31 まで可能）。"""
    return _token_request({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": os.environ["X_ACCESS_TOKEN"],
        "subject_token_type": "urn:x:params:oauth:token-type:oauth1_token",
        "oauth_token_secret": os.environ["X_ACCESS_SECRET"],
    })


def access_token():
    """投稿に使うアクセストークンを返す。1回の実行で1度だけ更新し、新しいリフレッシュトークンをすぐ保存する。"""
    if "access" not in _cache:
        try:
            tok = _token_request({"grant_type": "refresh_token", "refresh_token": os.environ["X_REFRESH_TOKEN"]})
        except TokenError as e:
            # 期限切れ・使用済みなど。公式の例にならい、旧方式のキーで交換し直す（2027-01-31 まで可能）
            if e.status != 400 or not (os.environ.get("X_ACCESS_TOKEN") and os.environ.get("X_ACCESS_SECRET")):
                raise
            print(f"::warning::[X] リフレッシュトークンが使えないため交換し直します: {e}")
            tok = exchange_oauth1()
        # 使い捨てなので、投稿より先に保存する（保存に失敗したら投稿せずエラーにする）
        save_refresh_token(tok["refresh_token"])
        _cache["access"] = tok["access_token"]
    return _cache["access"]


def enabled():
    return all(os.environ.get(k) for k in ("X_CLIENT_ID", "X_CLIENT_SECRET", "X_REFRESH_TOKEN"))


def whoami(token):
    r = requests.get("https://api.x.com/2/users/me", headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"X API エラー {r.status_code}: {r.text}")
    return r.json()["data"]["username"]


def setup():
    tok = exchange_oauth1()
    save_refresh_token(tok["refresh_token"])
    scope = tok.get("scope", "")
    print(f"[X] OAuth 2.0 に交換しました（scope: {scope or '不明'}）。X_REFRESH_TOKEN を保存しました")
    if "tweet.write" not in scope.split():
        print("::warning::[X] scope に tweet.write がありません。X アプリの権限が「Read and write」か確認してください")
    print(f"[X] 新しい方式での確認OK: @{whoami(tok['access_token'])}")


if __name__ == "__main__":
    if sys.argv[1:] == ["setup"]:
        setup()
    else:
        sys.exit("使い方: python scripts/x_oauth2.py setup")
