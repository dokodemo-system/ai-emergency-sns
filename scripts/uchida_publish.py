"""【試作】posts-uchida/<dir>/post.json を、設定で選んだ投稿先に出し、結果をスプシの「実行ログ」に書く。

GitHub Actions（uchida-publish）から呼ばれる。キー類は GitHub Secrets から環境変数で渡される。
公式LINE は試作ではイメージのみ（実際には送らない）。

使い方: python scripts/uchida_publish.py posts-uchida/2026-11-24-manual [...]
"""
import json
import sys
from pathlib import Path

import requests

import publish
import threads
import uchida_engine as eng
import x_oauth2


def to_instagram(post_dir, spec):
    uid = publish.ig_user_id()
    caption = spec["caption_ig"].strip()
    if spec.get("hashtags"):
        caption += "\n\n" + " ".join("#" + h.lstrip("#") for h in spec["hashtags"])
    if spec.get("type") == "reel":
        url = publish.media_url(post_dir, "reel.mp4")
        publish.wait_public(url)
        c = publish.ig_call("POST", f"{uid}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true")
    else:
        children = []
        for name in sorted(p.name for p in Path(post_dir).glob("[0-9][0-9].jpg")):
            url = publish.media_url(post_dir, name)
            publish.wait_public(url)
            children.append(publish.ig_call("POST", f"{uid}/media", image_url=url, is_carousel_item="true")["id"])
        for ch in children:
            publish.ig_wait(ch)
        c = publish.ig_call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)
    publish.ig_wait(c["id"])
    mid = publish.ig_call("POST", f"{uid}/media_publish", creation_id=c["id"])["id"]
    link = publish.ig_call("GET", mid, fields="permalink").get("permalink", "")
    return mid, link


def to_x(post_dir, spec):
    text = spec["x_text"].strip()
    if "http://" in text or "https://" in text:
        raise RuntimeError("X投稿にURLを含めない（リンク付きは高額課金のため）")
    r = requests.post("https://api.x.com/2/tweets", json={"text": text}, timeout=60,
                      headers={"Authorization": f"Bearer {x_oauth2.access_token()}"})
    if r.status_code >= 400:
        raise RuntimeError(f"X API エラー {r.status_code}: {r.text}")
    tid = r.json()["data"]["id"]
    return tid, f"https://x.com/ai_emergency_jp/status/{tid}"


def to_threads(post_dir, spec):
    me = threads.call("GET", "me", fields="id,username")
    uid, text = me["id"], threads.text_for(spec)
    children = []
    for name in sorted(p.name for p in Path(post_dir).glob("[0-9][0-9].jpg")):
        url = threads.media_url(post_dir, name)
        threads.wait_public(url)
        children.append(threads.call("POST", f"{uid}/threads", media_type="IMAGE", image_url=url, is_carousel_item="true")["id"])
    for ch in children:
        threads.wait_container(ch)
    c = threads.call("POST", f"{uid}/threads", media_type="CAROUSEL", children=",".join(children), text=text)
    threads.wait_container(c["id"])
    pid = threads.call("POST", f"{uid}/threads_publish", creation_id=c["id"])["id"]
    return pid, threads.call("GET", pid, fields="permalink").get("permalink", "")


JOBS = {"Instagram": to_instagram, "X": to_x, "Threads": to_threads}


def publish_dir(d):
    """1件分を、設定で選んだ投稿先に出して、スプシの実行ログに書く。全部成功なら True。"""
    d = d.rstrip("/")
    spec = json.loads(Path(d, "post.json").read_text(encoding="utf-8"))
    res, ids = {}, {}
    for name in spec.get("targets", []):
        if name == "公式LINE":
            res[name] = "友だちへ一斉配信（試作ではイメージ）"
            continue
        try:
            ids[name], res[name] = JOBS[name](d, spec)
            print(f"[{name}] 投稿しました: {res[name]}")
        except Exception as e:  # 1つ失敗しても、ほかの投稿先は続ける
            res[name] = f"失敗：{e}"[:300]
            print(f"::error::[{name}] {d}: {e}")
    ok = not any(str(v).startswith("失敗") for v in res.values())
    print(eng.gas_log(date=spec["date"].replace("-", "/"), mode=spec.get("mode", ""), design=spec.get("design", ""),
                      result="投稿しました" if ok else "一部失敗（内田さんへ LINE でアラート・試作ではイメージ）",
                      instagram=res.get("Instagram", "（投稿先に含めない）"), x=res.get("X", "（投稿先に含めない）"),
                      threads=res.get("Threads", "（投稿先に含めない）"), line=res.get("公式LINE", "（投稿先に含めない）"),
                      memo="ids " + json.dumps(ids)))
    return ok


if __name__ == "__main__":
    sys.exit(0 if all([publish_dir(d) for d in sys.argv[1:]]) else 1)
