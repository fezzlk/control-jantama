"""手動ブートストラップ用スクリプト。

テンプレート画像（共有アイコン・ダイアログ目印・コピーボタン）を用意するために、
一度だけ実行してブラウザで雀魂にログイン・画面遷移した後の全体スクリーンショットを保存する。
保存された assets/screenshots/reference.png を任意の画像編集ツールで開き、
必要なアイコンを切り出して assets/templates/ 配下に保存すること
（例: share_icon.png, dialog_marker.png, copy_button.png）。

将来のtrainer（画面記録UI）が実装されるまでの暫定的な手動ステップ。
"""

from __future__ import annotations

from pathlib import Path

from control_jantama.browser import get_or_create_page, launch_context, wait_for_human_navigation

OUTPUT_PATH = Path("assets/screenshots/reference.png")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with launch_context() as context:
        page = get_or_create_page(context)
        wait_for_human_navigation(
            "ブラウザが開きました。テンプレートを作りたい画面まで手動で移動したら Enter を押してください。"
        )
        page.screenshot(path=str(OUTPUT_PATH))
        print(f"保存しました: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
