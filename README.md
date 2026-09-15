# control-jantama

汎用的な視覚操作・画面学習ベースのブラウザ自動操作基盤（雀魂の牌譜URL取得を最初のユースケースとする）

## 現状

雀魂の牌譜一覧画面をスクロールしながら、表示されている各行の共有URLを取得し、SQLiteへ記録する（重複URLはDB側で自動的にスキップ）。

## セットアップ

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## テンプレート画像の準備（初回のみ・手動）

このPoCは共有アイコン等をテンプレートマッチングで検出する。まだ`assets/templates/`に画像が無いため、以下の手順で一度だけ作成する。

1. `python -m scripts.capture_reference_screenshot` を実行する。ブラウザが開いたら雀魂へ手動でログインする。
2. 撮影したい画面（例: 牌譜一覧画面）まで操作したらターミナルで Enter を押す → `assets/screenshots/reference_1.png` が保存される。
   - ブラウザは閉じないので、続けて共有ボタンを押してダイアログを表示させ、再度ターミナルで Enter を押す → `assets/screenshots/reference_2.png` が保存される。
   - 必要な画面を撮り終えるまで、この「操作してEnter」を何度でも繰り返せる。
3. 終わったらターミナルで `q` を入力してEnterを押すとブラウザが閉じる。
4. 保存された各`reference_N.png`を任意の画像編集ツールで開き、共有アイコン・共有ダイアログの目印になる要素（・必要ならコピーボタン）を切り出し、それぞれ `assets/templates/share_icon.png`・`assets/templates/dialog_marker.png`（・`assets/templates/copy_button.png`）として保存する。

これらの画像は実際の雀魂画面のスクリーンショットに由来するため`.gitignore`でコミット対象外にしている。将来的にはこの手動ステップをtrainer（画面記録UI）で置き換える予定。

## 実行

```bash
python -m control_jantama.scrape_replay_urls
```

ブラウザが開くので、雀魂へ手動でログインし牌譜一覧画面を表示してから Enter を押す。以降は自動で、画面内に表示されている各行の共有アイコンをクリック→ダイアログ出現確認→URL取得→SQLite保存→ダイアログを閉じる、を繰り返し、スクロールして雀魂側の遅延ロードを待ちながら次の行へ進む。スクロールしても新しい行が現れなくなったら一覧末尾に到達したとみなして終了する（`CONTROL_JANTAMA_MAX_SCROLL_STEPS`でスクロール回数の上限も設定可能）。

既に記録済みのURLはSQLiteのUNIQUE制約により自動的にスキップされるため、同じ行を複数回取得しても重複保存されない。

実行中は行ごとに取得結果と所要時間が表示され（例: `row 1: saved https://... (2.3s)`）、成功時は最後に合計時間・平均時間つきのサマリが表示される:

```
SUCCESS: saved 12 new url(s), skipped 3 duplicate(s) across 5 scroll step(s) in 42.1s (avg 2.8s/row over 15 row(s)), saved to data/replay_urls.sqlite3
```

確認:

```bash
sqlite3 data/replay_urls.sqlite3 "SELECT * FROM replay_urls;"
```

## テスト

```bash
pytest
```

## このPoCで対象外にしていること（意図的な先送り）

- 中断・再開チェックポイント
- 宣言的YAML workflowエンジン
- OCRによるURL抽出（クリップボード読み取りを優先する設計のため）
- 未知画面への画像LLMエスカレーション
- trainer（画面記録UI）— 現状は手動スクリーンショット+手動クロップで代替
- **Docker化** — このPoCは雀魂へのログイン・CAPTCHA対応を人間が目視で行う必要があるため、ローカルでheaded起動する前提としている。`docker compose up`一コマンド起動は、ログイン済みセッションを使ったheadless自動実行の「安定版」フェーズで導入する。

## 注意

- `data/`・`assets/templates/`・`assets/screenshots/`配下の実データ（ログインセッション、スクリーンショット、テンプレート画像、取得したURLのDB）は個人の雀魂アカウントに紐づく情報のため、`.gitignore`でコミット対象外にしている。
- 雀魂への短時間大量アクセスやアカウント自動操作には規約・アカウント制限リスクがある。取得間隔・最大件数などの制御は今後のフェーズで追加する。
