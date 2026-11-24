# 【試作】内田さん向け SNS自動投稿（uchida-demo ブランチ）

AI救急の毎日の投稿とは別の、**試作のデモ**です。入力はスプレッドシート（または専用画面）、出力は設定で選んだ「毎日入れる／自動で作る」。
このブランチでは `CLAUDE.md` の「毎日の手順」は実行しない。下の手順だけを行う。

## 手順（定期実行の Claude が行う）

0. `bash scripts/setup.sh`
1. `git fetch origin uchida-demo && git checkout uchida-demo`
2. 定期実行の指示文にある `UCHIDA_GAS_URL` と `UCHIDA_TOKEN` を export する（値はファイルやコミットに書かない）。
3. `python scripts/uchida_engine.py fetch`（スプシを読む）
4. `python scripts/uchida_engine.py build` の最後の行を見る：
   - `EMPTY <日付>` … 「毎日入れる」なのにその日の行が空。`python scripts/uchida_engine.py alert` を実行して終了（push しない）。
   - `MANUAL <dir>` … スプシに入っている文言をそのまま使う。**文言は一切変えない**。5 へ。
   - `AUTO <dir>` … `demo/context.json`（曜日テーマ・お店の情報・ルール・実績）を読み、`<dir>/post.json` の `theme` `slides` `caption_ig` `hashtags` `x_text` を書く。
     `date` `mode` `design` `targets` `source` `type` は変えない。形式は `CLAUDE.md` の「post.json の形式」に従う。
     ルールは厳守（架空の事例を作らない・実績は facts にあるものだけ・保証表現禁止・X本文にURL禁止・ハッシュタグ8〜12個・最後のスライドは cta）。
5. `python scripts/uchida_engine.py render <dir>` で画像を作り、**全部の画像を Read で目視確認**する。
   - AUTO のときは、はみ出し・誤字があれば post.json を直して作り直す。
   - MANUAL のときは文言を直さない（気づいた点は最後に報告するだけ）。
6. `git add <dir> && git commit -m "uchida: <dir>" && git push origin uchida-demo`
   （push すると Actions の uchida-publish が、設定で選んだ投稿先に出し、スプシの実行ログに結果を書く）
7. 最後に、作り方・デザイン・テーマ・表紙の見出し・投稿先を短く報告する。
