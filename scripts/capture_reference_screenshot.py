"""手動ブートストラップ用スクリプト。

テンプレート画像（共有アイコン・ダイアログ目印・コピーボタン）を用意するために、
同じブラウザセッション内で何度でもスクリーンショットを撮影できる。
例: 1回目は牌譜一覧画面（共有アイコン用）、2回目は共有ボタンを押した後の
ダイアログ表示画面（ダイアログ目印・コピーボタン用）。

Enterのたびにその時点の画面を1枚保存し、`q` + Enterで終了する。
保存された assets/screenshots/reference_N.png を任意の画像編集ツールで開き、
必要なアイコンを切り出して assets/templates/ 配下に保存すること
（例: share_icon.png, dialog_marker.png, copy_button.png）。

将来のtrainer（画面記録UI）が実装されるまでの暫定的な手動ステップ。
"""

from __future__ import annotations

from pathlib import Path

from control_jantama.browser import get_or_create_page, launch_context

OUTPUT_DIR = Path("assets/screenshots")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with launch_context() as context:
        page = get_or_create_page(context)

        print("ブラウザが開きました。雀魂へ手動でログインしてください。")
        print("スクリーンショットを撮りたい画面（一覧画面、ダイアログ表示中など）まで")
        print("操作したら Enter を押してください。何度でも撮影できます。")
        print("撮影を終えてブラウザを閉じる場合は q を入力して Enter を押してください。")

        count = 0
        while True:
            answer = input("> ")
            if answer.strip().lower() == "q":
                break
            count += 1
            path = OUTPUT_DIR / f"reference_{count}.png"
            page.screenshot(path=str(path))
            print(f"保存しました: {path}")

        print(f"終了します（{count}枚保存）。")


if __name__ == "__main__":
    main()
