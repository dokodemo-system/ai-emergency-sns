"""Instagram のフォロー候補リストを作り、GitHub Issue として毎朝届ける（フォロー自体はしない）。

- ターゲット側（事業者が自分で使う）ハッシュタグの最近の投稿を集める
- 売る側（支援・コンサル・集客代行など）っぽい投稿は除外する
- 結果を Markdown で標準出力し、ワークフローが Issue にする

Instagram のハッシュタグ検索は「7日間で30種類まで」の制限があるため、TAGS は30未満に保つこと。
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import requests

GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
TOKEN = os.environ["IG_ACCESS_TOKEN"]
PER_DAY_TAGS = 4
MAX_ITEMS = 8

TAGS = {
    "ネットショップ・物販": ["ネットショップ運営", "ネットショップ開業", "BASEショップ", "EC担当者"],
    "塾・スクール": ["塾長", "学習塾経営", "個別指導塾", "スクール運営"],
    "中小企業・事務": ["小さな会社", "社長の日常", "総務の仕事", "事務職"],
}
# 売る側・同業・勧誘っぽい投稿を除外するキーワード
SELLER_WORDS = ["支援", "コンサル", "集客", "代行", "DX", "コーチ", "副業", "稼", "起業塾", "無料相談", "公式LINE",
                "プレゼント", "セミナー", "講座", "マーケ", "フォロバ", "相互", "PR", "広告", "SNS運用", "Web制作", "HP制作"]


def get(path, **params):
    params["access_token"] = TOKEN
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"{path}: {r.status_code} {r.text}")
    return r.json()


def ig_user_id():
    for p in get("me/accounts", fields="instagram_business_account").get("data", []):
        if p.get("instagram_business_account"):
            return p["instagram_business_account"]["id"]
    raise RuntimeError("Instagram ビジネスアカウントが見つかりません")


def main():
    uid = ig_user_id()
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    # 日付で毎日違うタグの組み合わせにする（全体は12種類なので週30種類の制限内）
    rnd = random.Random(today.strftime("%Y%m%d"))
    pool = [(g, t) for g, ts in TAGS.items() for t in ts]
    picked = rnd.sample(pool, PER_DAY_TAGS)

    items, seen, errors = [], set(), []
    for group, tag in picked:
        try:
            hid = get("ig_hashtag_search", user_id=uid, q=tag)["data"][0]["id"]
            media = get(f"{hid}/recent_media", user_id=uid, limit=30,
                        fields="caption,permalink,timestamp,like_count,comments_count").get("data", [])
        except Exception as e:
            errors.append(f"#{tag}: {e}")
            continue
        for m in media:
            cap = (m.get("caption") or "").replace("\n", " ")
            if not m.get("permalink") or m["permalink"] in seen:
                continue
            if any(w.lower() in cap.lower() for w in SELLER_WORDS):
                continue
            if cap.count("#") > 25:  # タグだらけの投稿（業者っぽい）は除外
                continue
            seen.add(m["permalink"])
            items.append((group, tag, m, cap))

    rnd.shuffle(items)
    items = items[:MAX_ITEMS]

    out = [f"## 今日のフォロー候補（{today:%m/%d}）", "",
           "リンクを開いて、**事業そのもの（お店・教室・会社）のアカウントなら**フォロー＋ひと言コメント。",
           "プロフィールに「支援」「コンサル」「集客」などがあれば売る側なので飛ばしてください。", ""]
    if not items:
        out.append("今日は条件に合う投稿が見つかりませんでした。")
    for i, (group, tag, m, cap) in enumerate(items, 1):
        excerpt = cap[:70] + ("…" if len(cap) > 70 else "")
        out += [f"- [ ] **{i}. {group}**（#{tag}）　❤️{m.get('like_count', 0)} 💬{m.get('comments_count', 0)}",
                f"  {m['permalink']}", f"  > {excerpt}", ""]
    out += ["---", "### コメントのコツ",
            "- 投稿の中身に触れる（例：「〇〇の工夫、参考になります」）。宣伝やDM誘導はしない",
            "- 1日のフォローは最初の1週間は5人まで、その後も20人まで",
            "- 困りごと（集計・フォーム・自動化）を書いている人がいたら、解決のヒントをコメントするのが一番効果的"]
    if errors:
        out += ["", "<details><summary>取得できなかったタグ</summary>", ""] + [f"- {e}" for e in errors] + ["</details>"]
    print("\n".join(out))
    if errors:
        print("\n".join(errors), file=sys.stderr)
    if errors and not items:
        sys.exit(1)


if __name__ == "__main__":
    main()
