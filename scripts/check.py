"""キーの動作確認（投稿はしない）。GitHub Actions の check ワークフローから実行する。"""
import os
import sys

import requests

GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
ok = True


def get(path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    return requests.get(f"{GRAPH}/{path}", params=params, timeout=60)


if os.environ.get("IG_ACCESS_TOKEN"):
    r = get("me/accounts", fields="name,instagram_business_account{username}")
    if r.status_code != 200:
        ok = False
        print(f"::error::[Instagram] キーでページが取得できません: {r.text}")
    else:
        pages = r.json().get("data", [])
        print(f"[Instagram] 管理できるページ: {[p['name'] for p in pages]}")
        ig = next((p["instagram_business_account"] for p in pages if p.get("instagram_business_account")), None)
        if not ig:
            ok = False
            print("::error::[Instagram] ページに Instagram ビジネスアカウントがつながっていません")
        else:
            print(f"[Instagram] 投稿先: @{ig.get('username')}")
            lim = get(f"{ig['id']}/content_publishing_limit", fields="quota_usage,config")
            if lim.status_code == 200:
                print(f"[Instagram] 投稿権限OK（24時間の投稿数: {lim.json()}）")
            else:
                ok = False
                print(f"::error::[Instagram] 投稿権限の確認に失敗: {lim.text}")
    d = get("debug_token", input_token=os.environ["IG_ACCESS_TOKEN"])
    if d.status_code == 200:
        exp = d.json().get("data", {}).get("expires_at")
        print(f"[Instagram] キーの有効期限: {'期限なし' if exp == 0 else exp}")
else:
    print("[Instagram] キー未設定")

if all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
    from requests_oauthlib import OAuth1
    auth = OAuth1(os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
                  os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"])
    r = requests.get("https://api.x.com/2/users/me", auth=auth, timeout=60)
    if r.status_code == 200:
        print(f"[X] 投稿先: @{r.json()['data']['username']}")
    else:
        ok = False
        print(f"::error::[X] キーの確認に失敗 {r.status_code}: {r.text}")
else:
    print("[X] キー未設定")

sys.exit(0 if ok else 1)
