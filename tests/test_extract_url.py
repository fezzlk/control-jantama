from control_jantama.poc_scrape_one_replay_url import extract_url, is_valid_replay_url


def test_extract_url_strips_japanese_label_prefix():
    # 実機確認(2026-09-15): 雀魂のコピー結果は説明文付き
    text = "雀魂牌譜:https://game.mahjongsoul.com/?paipu=260914-e72928a0-0018-4be8-bf33-ea9e3c2d53e3_a439414237"

    url = extract_url(text)

    assert url == "https://game.mahjongsoul.com/?paipu=260914-e72928a0-0018-4be8-bf33-ea9e3c2d53e3_a439414237"


def test_extract_url_returns_none_when_no_url_present():
    assert extract_url("コピーに失敗しました") is None


def test_is_valid_replay_url_accepts_mahjongsoul_domain():
    assert is_valid_replay_url("https://game.mahjongsoul.com/?paipu=abc") is True


def test_is_valid_replay_url_rejects_non_matching_domain():
    assert is_valid_replay_url("https://example.com/?paipu=abc") is False
