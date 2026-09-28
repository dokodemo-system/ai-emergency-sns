# AI救急 SNS自動投稿

株式会社ドコデモどあ（代表：飯田宏之）が運営する「AI救急」の Instagram / X 投稿を毎日作るリポジトリ。
目的は**仕事の受注**：投稿 → プロフィール → DM「診断」→ 無料診断15分 → 受注。

- Instagram / X: `@ai_emergency_jp`
- 投稿は `claude/posts` ブランチに `posts/YYYY-MM-DD/` を push すると、GitHub Actions（`.github/workflows/publish.yml`）が自動で投稿する。
- Claude はキー類を持たない。投稿そのものは Actions が行う。

## 毎日の手順（クラウドの定期実行で行う）

0. `bash scripts/setup.sh` で道具（画像書き出し・日本語フォント・ffmpeg）を準備する。
1. `git fetch origin claude/posts` し、存在すれば `git checkout claude/posts`（`origin/main` を取り込む：`git merge --no-edit origin/main`）。存在しなければ `git checkout -b claude/posts`。
2. 今日の日付（Asia/Tokyo）を `TZ=Asia/Tokyo date +%F` で取得。`posts/<今日>/` が既にあれば、**投稿づくり（3〜6）は飛ばして 7 へ**（二重投稿防止）。
3. 投稿内容を決める：
   - `content/queue/NN.json` のうち、`posts/*/post.json` の `source` にまだ `queue:NN` が無いものがあれば、**一番小さい番号**を `posts/<今日>/post.json` にコピーし、`date` と `source`（`queue:NN`）を書き込んで使う（内容は変えない）。
   - queue を使い切ったら、`content/themes.md` の曜日テーマに沿って新しく作る。直近14日分の `posts/*/post.json` を読み、同じ切り口・同じ見出しを避ける。
4. `content/rules.md`（厳守）、`content/brand.md`、`content/facts.md` を読んだうえで `posts/<今日>/post.json` を書く（形式は下記）。
5. `python scripts/render.py posts/<今日>` で画像（と reel なら動画）を作る。
6. **できた画像を全部 Read で目視確認**する。文字のはみ出し・不自然な改行・重なり・誤字があれば post.json を直して再生成。問題がなくなるまで繰り返す。
7. **フォロー候補を探す**（下の「フォロー候補の探し方」）。`candidates/<今日>.md` が既にあれば飛ばす。
8. `git add posts candidates && git commit -m "post: <今日> <テーマ>" && git push origin claude/posts`（変更が無ければ何もしない）
9. 最後に、作った投稿の要約（テーマ・見出し・X本文）と、候補の件数を出力して終了。

## フォロー候補の探し方（毎朝・0円）

飯田さんが手動でフォロー・コメント・返信するための候補リストを作る。**フォローやコメント自体は絶対にしない**（規約違反）。

1. WebSearch で、次のような検索を**毎日3〜5本**行う（毎日少しずつ言葉を変える。業種は themes.md の順番で回す）：
   - Instagram の事業者：`site:instagram.com 塾長 個別指導`、`site:instagram.com ネットショップ 店主 発送`、`site:instagram.com 小さな会社 社長 日常` など
   - 困りごとの投稿：`GAS エラー 動かない 困った`、`スプレッドシート 自動 集計 止まった`、`お問い合わせフォーム 届かない WordPress 困った`、`ChatGPT で作った スクリプト 動かない` など（X・note・ブログ・Q&Aサイト）
2. 見つかったページから、**5〜8件**選ぶ。選ぶ基準：
   - ○ お店・教室・小さな会社そのもののアカウント、または事業者本人が困りごとを書いている投稿
   - × 「支援」「コンサル」「集客」「制作」「DX」などを売る側（同業者）、個人の私生活アカウント、1年以上前の投稿、企業の大手アカウント
   - 直近30日の `candidates/*.md` に出したURLは除く
3. `candidates/<今日>.md` を次の形で書く（個人情報は書かない。公開URLと、公開されている事業の種類だけ）：

```markdown
## フォロー候補（MM/DD）

- [ ] **1. 学習塾（Instagram）** https://...
  - 理由：教室運営の日常を投稿している塾のアカウント
  - コメント案：「〇〇の取り組み、生徒さんのやる気が出そうですね」
- [ ] **2. 困りごと（X）** https://...
  - 内容：GASのトリガーが急に止まったと投稿
  - 返信案：「実行ログにエラーが出ていないか見てみてください。権限の再承認で直ることも多いです」
```

   - コメント・返信案は**役に立つ一言だけ**。宣伝・DM誘導・「AI救急」の名前は入れない。
   - 1件も見つからなければ「今日は見つかりませんでした」と書く。
4. X の投稿はネット検索にほとんど出ないので、**リストの最後に必ず次の「X の検索リンク」をそのまま付ける**（飯田さんが押すだけで最新の困りごと投稿が見られる）：

```markdown
---
### X で困っている人を探す（押すと最新の投稿が出ます）
- [GAS エラー](https://x.com/search?q=GAS%20%E3%82%A8%E3%83%A9%E3%83%BC%20lang%3Aja%20-filter%3Alinks&f=live)
- [GAS 動かない](https://x.com/search?q=GAS%20%E5%8B%95%E3%81%8B%E3%81%AA%E3%81%84%20lang%3Aja%20-filter%3Alinks&f=live)
- [スプレッドシート 動かなくなった](https://x.com/search?q=%E3%82%B9%E3%83%97%E3%83%AC%E3%83%83%E3%83%89%E3%82%B7%E3%83%BC%E3%83%88%20%E5%8B%95%E3%81%8B%E3%81%AA%E3%81%8F%E3%81%AA%E3%81%A3%E3%81%9F%20lang%3Aja%20-filter%3Alinks&f=live)
- [問い合わせフォーム 届かない](https://x.com/search?q=%E5%95%8F%E3%81%84%E5%90%88%E3%82%8F%E3%81%9B%E3%83%95%E3%82%A9%E3%83%BC%E3%83%A0%20%E5%B1%8A%E3%81%8B%E3%81%AA%E3%81%84%20lang%3Aja%20-filter%3Alinks&f=live)
- [ChatGPT GAS 動かない](https://x.com/search?q=ChatGPT%20GAS%20%E5%8B%95%E3%81%8B%E3%81%AA%E3%81%84%20lang%3Aja%20-filter%3Alinks&f=live)
- [自動化 止まった 困った](https://x.com/search?q=%E8%87%AA%E5%8B%95%E5%8C%96%20%E6%AD%A2%E3%81%BE%E3%81%A3%E3%81%9F%20%E5%9B%B0%E3%81%A3%E3%81%9F%20lang%3Aja%20-filter%3Alinks&f=live)

返信は「役に立つ一言」だけ。売り込み・DM誘導はしない（プロフィールを見て、向こうから来てもらう）。
```

## post.json の形式

```json
{
  "date": "2026-10-01",
  "source": "queue:01 | theme:火",
  "type": "carousel",
  "theme": "止まる原因の解説",
  "slides": [
    {"kind": "cover", "tag": "よくある原因", "title": "…\n[[強調]]", "lead": "…→"},
    {"kind": "list", "tag": "…", "title": "…", "items": ["…"], "icon": "q", "lead": "…"},
    {"kind": "cta"}
  ],
  "caption_ig": "キャプション本文（改行可）",
  "hashtags": ["GAS", "業務効率化"],
  "x_text": "Xの本文（140字目安・URL禁止）"
}
```

- `type`: `carousel`（画像2〜10枚）または `reel`（スライドを動画化。3〜6枚、1枚3秒）。
- スライドの `kind`：
  - `cover` {tag, title, lead, size?, mock?{label, bars[], error}} … 表紙（紺）
  - `list` {tag, title, items[], icon: x|v|q, lead, dark?} … 箇条書き（x=症状 v=できる q=チェック）
  - `steps` {tag, title, items[{h,p}], lead, rank?, start?} … 番号付き
  - `grid` {tag, title, items[{h,p}]×4, lead}
  - `prices` {tag, title, items[{n,d,y}], lead}
  - `qa` {tag, title, items[{q,a}]}
  - `message` {tag, text, lead, size?, brand?} … 大きな一言（リール向き）
  - `cta` {} … 最後のお申し込み案内（**必ず最後に1枚**）
- 記法：`[[強調]]`=赤字、`**太字**`、`\n`=改行。
- 文字量の目安：cover の title は1行11字×3行まで。list は4項目・1項目18字まで。steps は3〜4項目。
