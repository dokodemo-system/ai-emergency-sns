# 【試作】内田さん向け SNS自動投稿（uchida-demo ブランチ）

AI救急の毎日の投稿とは別の、**試作のデモ**です。入力はスプレッドシート（または専用画面）、出力は設定で選んだ「毎日入れる／自動で作る」。
このブランチでは `CLAUDE.md` の「毎日の手順」は実行しない。

## 全体の流れ

1. 実行の合図（`demo/run.txt` の更新）→ GitHub Actions の uchida-run がスプシを読む
   - 毎日入れる：その日の行をそのまま画像にして投稿（行が空なら投稿せずアラート）
   - 自動で作る：材料（`demo/context.json`）と、中身が空の `posts-uchida/<日付>-auto/post.json` を置く
2. 自動で作るのときだけ、定期実行の Claude が中身を書いて push する（下の手順）
3. push を受けて uchida-run が、設定のデザイン見本で画像を作り、設定の投稿先に出し、スプシの実行ログに書く

## 定期実行の Claude の手順（自動で作るの中身を書く）

1. `git fetch origin uchida-demo && git checkout uchida-demo && git pull`
2. `posts-uchida/*-auto/post.json` のうち `slides` が空のものを探す。無ければ「書く対象なし」と報告して終了。
3. `demo/context.json`（曜日テーマ・お店の情報・ルール・実績）を読み、その post.json の `theme` `slides` `caption_ig` `hashtags` `x_text` を書く。
   - `date` `mode` `design` `targets` `source` `type` は変えない。形式は `CLAUDE.md` の「post.json の形式」に従う。
   - ルール厳守：架空の事例を作らない（実績は context の facts にあるものだけ）・保証表現禁止・X本文にURL禁止・ハッシュタグ8〜12個・最後のスライドは cta。
   - 文字量：cover の title は1行11字×3行まで、list は4項目・1項目18字まで、steps は3〜4項目。
4. `python3 -c "import json;json.load(open('<dir>/post.json'))"` で形式を確認する。
5. `git add <dir>/post.json && git commit -m "uchida: 自動で作った中身 <dir>" && git push origin uchida-demo`
6. テーマ・表紙の見出し・X本文を短く報告する。
