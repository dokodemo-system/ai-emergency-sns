# AI救急 SNS自動投稿

毎朝クラウドの Claude が投稿（画像・文章）を作り、`claude/posts` ブランチに push → GitHub Actions が Instagram と X に投稿します。

- 作り方・ルール：`CLAUDE.md`、`content/`
- 最初の9投稿：`content/queue/01.json`〜`09.json`（1日1本ずつ消化）
- 投稿の記録：Actions タブの「publish」／`claude/posts` ブランチの `posts/`

## キー（GitHub → Settings → Secrets and variables → Actions）
| 名前 | 中身 |
|---|---|
| IG_USER_ID | （任意）Instagram ビジネスアカウントのID。未設定ならトークンから自動で探す |
| IG_ACCESS_TOKEN | Meta のシステムユーザーのアクセストークン（無期限） |
| X_API_KEY / X_API_SECRET | X アプリの API Key / Secret |
| X_ACCESS_TOKEN / X_ACCESS_SECRET | X の Access Token / Secret（読み書き権限） |
| X_CLIENT_ID / X_CLIENT_SECRET | X アプリの OAuth 2.0 Client ID / Client Secret |
| X_REFRESH_TOKEN | X の OAuth 2.0 リフレッシュトークン。**手で入れない**（x-oauth2-setup と毎回の投稿が自動で書き換える） |
| SECRETS_PAT | 上の X_REFRESH_TOKEN を書き換えるための GitHub のトークン（このリポジトリの Secrets の書き込み権限だけ） |

未設定の媒体はスキップされます。X は X_REFRESH_TOKEN があれば OAuth 2.0、なければ OAuth 1.0a（2027-01-31 で終了）で投稿します。

## X を OAuth 2.0 に切り替える（1回だけ）
1. X_CLIENT_ID / X_CLIENT_SECRET / SECRETS_PAT を上の場所に登録する
2. Actions → x-oauth2-setup → Run workflow（投稿はしない。最後に @ユーザー名 が出れば成功）
3. Actions → check → Run workflow で「（OAuth 2.0）」と出ることを確認

X_REFRESH_TOKEN は使い捨てで、投稿のたびに新しい値に入れ替わります。約6か月使わないと失効するので、自動投稿を長く止めたあとは 2 をやり直してください（2027-01-31 以降はやり直し方が変わります）。

## 止めたいとき
claude.ai/code/routines で定期実行をオフにする。
