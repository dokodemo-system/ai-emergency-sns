"""Threads に投稿する（Threads API）。

画像は Instagram と同じく jsDelivr の公開URLで渡す。本文は post.json の threads_text、
無ければ caption_ig を使う（500文字まで。ハッシュタグは付けない：Threads は1投稿にタグ1つのため）。
キー（THREADS_ACCESS_TOKEN）は GitHub Secrets から環境変数で渡される（Claude には渡らない）。

使い方: python scripts/threads.py posts/2026-11-23
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

GRAPH = "https://graph.threads.net/v1.0"
REPO = os.environ.get("GITHUB_REPOSITORY", "dokodemo-system/ai-emergency-sns")
LIMIT = 500


def media_url(post_dir, name):
    # 画像があるコミットを指す（テスト用ワークフローでは claude/posts のコミットを MEDIA_SHA で渡す）
    sha = os.environ.get("MEDIA_SHA") or os.environ.get("GITHUB_SHA", "main")
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{post_dir}/{name}"


def wait_public(url, tries=10):
    for _ in range(tries):
        if requests.head(url, timeout=30, allow_redirects=True).status_code == 200:
            return
        time.sleep(6)
    raise RuntimeError(f"公開URLが取得できません: {url}")


def call(method, path, **params):
    params["access_token"] = os.environ["THREADS_ACCESS_TOKEN"]
    r = requests.request(method, f"{GRAPH}/{path}", params=params, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Threads API エラー {r.status_code}: {r.text}")
    return r.json()


def wait_container(cid, tries=10):
    # 公式の推奨どおり、公開前に処理完了を待つ（30秒ごと・最大5分）
    for _ in range(tries):
        time.sleep(30)
        st = call("GET", cid, fields="status,error_message")
        if st.get("status") == "FINISHED":
            return
        if st.get("status") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Threads の処理に失敗: {cid} {st}")
    raise RuntimeError("Threads の処理がタイムアウトしました")


def text_for(spec):
    text = (spec.get("threads_text") or spec["caption_ig"]).strip()
    if len(text) > LIMIT:  # 長すぎるときは、500字以内の最後の改行で切る
        cut = text[:LIMIT].rfind("\n")
        text = text[:cut if cut > 0 else LIMIT].rstrip()
    return text


def post_threads(post_dir, spec):
    me = call("GET", "me", fields="id,username")
    uid = me["id"]
    text = text_for(spec)
    if spec.get("type") == "reel":
        url = media_url(post_dir, "reel.mp4")
        wait_public(url)
        c = call("POST", f"{uid}/threads", media_type="VIDEO", video_url=url, text=text)
    else:
        children = []
        for name in sorted(p.name for p in Path(post_dir).glob("[0-9][0-9].jpg")):
            url = media_url(post_dir, name)
            wait_public(url)
            children.append(call("POST", f"{uid}/threads", media_type="IMAGE", image_url=url,
                                 is_carousel_item="true")["id"])
        for ch in children:
            wait_container(ch)
        c = call("POST", f"{uid}/threads", media_type="CAROUSEL", children=",".join(children), text=text)
    wait_container(c["id"])
    res = call("POST", f"{uid}/threads_publish", creation_id=c["id"])
    link = call("GET", res["id"], fields="permalink").get("permalink", "")
    print(f"[Threads] 投稿しました（@{me.get('username')}）: {post_dir} id={res['id']} {link}")


if __name__ == "__main__":
    d = sys.argv[1].rstrip("/")
    post_threads(d, json.loads(Path(d, "post.json").read_text(encoding="utf-8")))
