"""GitHub Actions から呼ばれ、新しく追加された投稿を Instagram と X に出す。

キー類は GitHub Secrets から環境変数で渡される（Claude には渡らない）。
キーが未設定の媒体はスキップする（準備中でも失敗しないように）。

使い方: python scripts/publish.py posts/2026-10-01 [posts/2026-10-02 ...]
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

REPO = os.environ.get("GITHUB_REPOSITORY", "dokodemo-system/ai-emergency-sns")
SHA = os.environ.get("GITHUB_SHA", "main")
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"


def media_url(post_dir, name):
    # jsDelivr はコミットSHA指定なら即時・不変で、正しい Content-Type で配信される
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{SHA}/{post_dir}/{name}"


def wait_public(url, tries=10):
    for _ in range(tries):
        r = requests.head(url, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return
        time.sleep(6)
    raise RuntimeError(f"公開URLが取得できません: {url}")


# ---------- Instagram ----------
def ig_call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{GRAPH}/{path}", data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Instagram API エラー {r.status_code}: {r.text}")
    return r.json()


def ig_wait(container_id, tries=40):
    for _ in range(tries):
        st = ig_call("GET", container_id, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram の処理に失敗: {container_id} {st}")
        time.sleep(10)
    raise RuntimeError("Instagram の処理がタイムアウトしました")


def post_instagram(post_dir, spec):
    uid = os.environ["IG_USER_ID"]
    caption = spec["caption_ig"].strip()
    if spec.get("hashtags"):
        caption += "\n\n" + " ".join("#" + h.lstrip("#") for h in spec["hashtags"])
    if spec.get("type") == "reel":
        url = media_url(post_dir, "reel.mp4")
        wait_public(url)
        c = ig_call("POST", f"{uid}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true")
        ig_wait(c["id"])
    else:
        imgs = sorted(p.name for p in Path(post_dir).glob("[0-9][0-9].jpg"))
        children = []
        for name in imgs:
            url = media_url(post_dir, name)
            wait_public(url)
            children.append(ig_call("POST", f"{uid}/media", image_url=url, is_carousel_item="true")["id"])
        for ch in children:
            ig_wait(ch)
        c = ig_call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)
        ig_wait(c["id"])
    res = ig_call("POST", f"{uid}/media_publish", creation_id=c["id"])
    print(f"[Instagram] 投稿しました: {post_dir} media_id={res.get('id')}")


# ---------- X ----------
def post_x(post_dir, spec):
    from requests_oauthlib import OAuth1
    text = spec["x_text"].strip()
    if "http://" in text or "https://" in text:
        raise RuntimeError("X投稿にURLを含めない（リンク付きは高額課金のため）")
    auth = OAuth1(os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
                  os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"])
    r = requests.post("https://api.x.com/2/tweets", json={"text": text}, auth=auth, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"X API エラー {r.status_code}: {r.text}")
    print(f"[X] 投稿しました: {post_dir} id={r.json()['data']['id']}")


def has(*names):
    return all(os.environ.get(n) for n in names)


def main(dirs):
    failed = False
    for d in dirs:
        d = d.rstrip("/")
        spec = json.loads(Path(d, "post.json").read_text(encoding="utf-8"))
        jobs = [("Instagram", ("IG_USER_ID", "IG_ACCESS_TOKEN"), post_instagram),
                ("X", ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"), post_x)]
        for name, keys, fn in jobs:
            if not has(*keys):
                print(f"[{name}] キー未設定のためスキップ: {d}")
                continue
            try:
                fn(d, spec)
            except Exception as e:  # 片方が失敗してももう片方は出す
                failed = True
                print(f"::error::[{name}] {d}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
