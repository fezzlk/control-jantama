# control-jantama

汎用的な視覚操作・画面学習ベースのブラウザ自動操作基盤（雀魂の牌譜URL取得を最初のユースケースとする）

## 現状

雀魂の牌譜一覧画面をスクロールしながら、表示されている各行の共有URLを取得し、SQLiteへ記録する（重複URLはDB側で自動的にスキップ）。

## 動作環境

- **OS**: macOS / Windows / Linux（Playwright Chromiumが動作する環境）を想定。**動作確認は現時点でmacOSのみ**。他OSでは以下の点で追加対応が必要になる可能性がある。
  - **Linux**: Chromium実行に必要な共有ライブラリが不足している場合、`playwright install-deps`（または各ディストリのパッケージマネージャでの手動導入）が別途必要。
  - **Windows**: venvの有効化コマンドが異なる（下記セットアップ参照）。以降の実行例にある`venv/bin/python`は`venv\Scripts\python.exe`に読み替える。DB確認に使う`sqlite3`コマンドは標準搭載されていないため、代わりにPythonの`sqlite3`モジュール等で読み替える。
- **ディスプレイ必須**: ブラウザを`headless=False`（画面表示あり）で起動し、雀魂へのログイン・CAPTCHA対応を人間が目視で行う設計のため、実際に画面を表示できる環境が必要。SSH接続のみのヘッドレスサーバーやディスプレイなしのコンテナでは、Xサーバー等を別途用意しない限り動作しない。
- **Python**: 3.11系（`.python-version`で固定）。`python3.11`コマンドが無い環境ではpyenv等で用意するか、セットアップのコマンドをその環境のPython 3.11実行コマンドに読み替える。
- **画面倍率・解像度**: OS側のディスプレイ拡大設定（Retina/HiDPI等）はコード側で`device_scale_factor=1`固定にして吸収しているため影響しない。ブラウザウィンドウは固定1280x800を使うため、モニタ解像度がそれを下回ると表示が乱れる可能性がある。
- **雀魂アカウント**: 実行者自身のアカウントで手動ログインする前提。アカウント貸与や自動ログインは想定していない（規約・アカウント制限リスクがあるため未対応）。
- **費用**: 追加の有料API等は使わない。初回`playwright install chromium`でbrowser本体（無料・100〜300MB程度）をネットワーク経由でダウンロードする。
- **テンプレート画像の環境依存**: 共有アイコン等の識別に使う画像は各利用者が自分の環境で手動作成する前提（下記「テンプレート画像の準備」）ため、OSやディスプレイが違っても仕組み上は個別対応できる。ただしGPU・ブラウザのレンダリング差で見た目が微妙に変わった場合、既定の一致閾値（`CONTROL_JANTAMA_MATCH_THRESHOLD=0.85`）で検出できない可能性は未検証。閾値を下げる、テンプレート画像を撮り直す等で調整する。

## セットアップ

```bash
python3.11 -m venv venv
source venv/bin/activate   # Windowsの場合: venv\Scripts\Activate.ps1 (PowerShell) または venv\Scripts\activate.bat (コマンドプロンプト)
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## テンプレート画像の準備（初回のみ・手動）

このPoCは共有アイコン等をテンプレートマッチングで検出する。まだ`assets/templates/`に画像が無いため、以下の手順で一度だけ作成する。

1. `venv/bin/python -m scripts.capture_reference_screenshot` を実行する。ブラウザが開いたら雀魂へ手動でログインする。
2. 撮影したい画面（例: 牌譜一覧画面）まで操作したらターミナルで Enter を押す → `assets/screenshots/reference_1.png` が保存される。
   - ブラウザは閉じないので、続けて共有ボタンを押してダイアログを表示させ、再度ターミナルで Enter を押す → `assets/screenshots/reference_2.png` が保存される。
   - 必要な画面を撮り終えるまで、この「操作してEnter」を何度でも繰り返せる。
3. 終わったらターミナルで `q` を入力してEnterを押すとブラウザが閉じる。
4. 保存された各`reference_N.png`を任意の画像編集ツールで開き、共有アイコン・共有ダイアログの目印になる要素（・必要ならコピーボタン）を切り出し、それぞれ `assets/templates/share_icon.png`・`assets/templates/dialog_marker.png`（・`assets/templates/copy_button.png`）として保存する。

これらの画像は実際の雀魂画面のスクリーンショットに由来するため`.gitignore`でコミット対象外にしている。将来的にはこの手動ステップをtrainer（画面記録UI）で置き換える予定。

## 実行

```bash
venv/bin/python -m control_jantama.scrape_replay_urls
```

（venvを`activate`済みのシェルであれば`python -m ...`でもよいが、`venv/bin/python`をフルパスで呼ぶ方がシェルの状態に依存せず確実）

ブラウザが開くので、雀魂へ手動でログインし牌譜一覧画面を表示してから Enter を押す。以降は自動で、画面内に表示されている各行の共有アイコンをクリック→ダイアログ出現確認→URL取得→SQLite保存→ダイアログを閉じる、を繰り返し、スクロールして雀魂側の遅延ロードを待ちながら次の行へ進む。スクロールしても新しい行が現れなくなったら一覧末尾に到達したとみなして終了する（`CONTROL_JANTAMA_MAX_SCROLL_STEPS`でスクロール回数の上限も設定可能）。

既に記録済みのURLはSQLiteのUNIQUE制約により自動的にスキップされるため、同じ行を複数回取得しても重複保存されない。

### 段位戦・友人戦の判別（後付けタグ付け）

雀魂の一覧画面・牌譜URLのどちらにもモード（段位戦/友人戦等）の情報は含まれていない。判別したい場合は`CONTROL_JANTAMA_MATCH_TYPE`を設定して実行し、ブラウザが開いたら（通常の「実行」と同様に）**Enterを押す前に**左サイドバーで対象タブ（例:「友人戦」）に切り替えてから進める。

```bash
CONTROL_JANTAMA_MATCH_TYPE=友人戦 venv/bin/python -m control_jantama.scrape_replay_urls
```

ブラウザは毎回新規に起動する（ログインセッションは`user_data_dir`で引き継がれるが、開いていたタブの状態は引き継がれない）ため、「友人戦」タブを先に開いておくことはできない。起動後に手動で切り替える。

既に「一覧」タブ（全モード混在）から取得済みのURLでも、`match_type`列が未設定(NULL)であれば重複扱いのままそこだけ後から埋められる（一度入った値を上書きすることはない）。

実行中は行ごとに取得結果と所要時間が表示され（例: `row 1: saved https://... (2.3s)`）、成功時は最後に合計時間・平均時間つきのサマリが表示される:

```
SUCCESS: saved 12 new url(s), skipped 3 duplicate(s) across 5 scroll step(s) in 42.1s (avg 2.8s/row over 15 row(s)), saved to data/replay_urls.sqlite3
```

確認:

```bash
sqlite3 data/replay_urls.sqlite3 "SELECT * FROM replay_urls;"
```

（`sqlite3`コマンドが無い場合は`python -c "import sqlite3; print(sqlite3.connect('data/replay_urls.sqlite3').execute('SELECT * FROM replay_urls').fetchall())"`でも確認できる）

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
