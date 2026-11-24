"""【試作】GitHub Actions（uchida-run）から呼ばれ、試作の1回分を動かす。

- demo/run.txt が変わった（＝実行の合図）：スプシを読んで設定を見る
    毎日入れる → その日の行から投稿データと画像を作り、投稿する（行が空ならアラート）
    自動で作る → 材料（demo/context.json）と空の投稿データを置く。中身は定期実行の Claude が書いて push する
- posts-uchida/*/post.json が変わった（＝Claude が中身を書いた）：画像を作り、投稿する

使い方: python scripts/uchida_ci.py <before> <sha>
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import uchida_engine as eng

ROOT = eng.ROOT


def git(*a, check=True):
    return subprocess.run(["git", *a], cwd=ROOT, check=check, capture_output=True, text=True).stdout.strip()


def commit_push(paths, msg):
    git("add", "-f", *paths)
    if not git("diff", "--cached", "--name-only"):
        return git("rev-parse", "HEAD")
    git("commit", "-q", "-m", msg)
    git("push", "-q", "origin", "HEAD:uchida-demo")
    return git("rev-parse", "HEAD")


def render_and_publish(post_dir):
    eng.cmd_render(post_dir)
    sha = commit_push([post_dir], f"uchida: 画像 {post_dir}")
    os.environ["MEDIA_SHA"] = sha  # 画像が入ったコミットを jsDelivr で配る
    import uchida_publish
    uchida_publish.publish.SHA = sha
    return uchida_publish.publish_dir(post_dir)


def main(before, sha):
    if not before or set(before) == {"0"}:
        before = git("merge-base", "origin/main", sha)
    changed = git("diff", "--name-only", before, sha).splitlines()
    ok = True
    if "demo/run.txt" in changed:
        eng.cmd_fetch()
        kind, val = eng.build()
        print(kind, val)
        if kind == "EMPTY":
            eng.cmd_alert()
            print("「毎日入れる」なのにその日の行が空 → 投稿せずアラート")
        elif kind == "MANUAL":
            commit_push([val], f"uchida: 投稿データ {val}")
            ok = render_and_publish(val)
        else:
            commit_push([val, "demo/context.json"], f"uchida: 自動で作る材料 {val}")
            print("自動で作る → 定期実行の Claude が中身を書いて push すると、続きが動く")
    for f in changed:
        p = Path(f)
        if p.parts[:1] == ("posts-uchida",) and p.name == "post.json" and (ROOT / f).exists():
            spec = json.loads((ROOT / f).read_text(encoding="utf-8"))
            if spec.get("slides") and not (ROOT / p.parent / "01.jpg").exists():
                ok = render_and_publish(p.parent.as_posix()) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(*(sys.argv[1:3] + [""] * 2)[:2])
