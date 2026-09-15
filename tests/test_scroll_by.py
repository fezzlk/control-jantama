from control_jantama.browser import scroll_by


class _FakeMouse:
    def __init__(self):
        self.wheel_calls: list[tuple[int, int]] = []

    def wheel(self, dx: int, dy: int) -> None:
        self.wheel_calls.append((dx, dy))


class _FakePage:
    def __init__(self):
        self.mouse = _FakeMouse()
        self.wait_calls: list[int] = []

    def wait_for_timeout(self, ms: int) -> None:
        self.wait_calls.append(ms)


def test_scroll_by_splits_total_into_ticks():
    page = _FakePage()

    scroll_by(page, total_px=250, tick_px=100, tick_interval_ms=10)

    assert [dy for _dx, dy in page.mouse.wheel_calls] == [100, 100, 50]
    assert page.wait_calls == [10, 10, 10]


def test_scroll_by_single_tick_when_total_smaller_than_tick():
    page = _FakePage()

    scroll_by(page, total_px=50, tick_px=100, tick_interval_ms=10)

    assert [dy for _dx, dy in page.mouse.wheel_calls] == [50]
