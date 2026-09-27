# AI救急 SNS自動投稿

毎朝クラウドの Claude が投稿（画像・文章）を作り、`claude/posts` ブランチに push → GitHub Actions が Instagram と X に投稿します。

- 作り方・ルール：`CLAUDE.md`、`content/`
- 最初の9投稿：`content/queue/01.json`〜`09.json`（1日1本ずつ消化）
- 投稿の記録：Actions タブの「publish」／`claude/posts` ブランチの `posts/`

## キー（GitHub → Settings → Secrets and variables → Actions）
| 名前 | 中身 |
|---|---|
| IG_USER_ID | Instagram ビジネスアカウントのID |
| IG_ACCESS_TOKEN | Meta のシステムユーザーのアクセストークン（無期限） |
| X_API_KEY / X_API_SECRET | X アプリの API Key / Secret |
| X_ACCESS_TOKEN / X_ACCESS_SECRET | X の Access Token / Secret（読み書き権限） |

未設定の媒体はスキップされます。

## 止めたいとき
claude.ai/code/routines で定期実行をオフにする。
