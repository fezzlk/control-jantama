from control_jantama.browser import drag_scroll_by, scroll_by


class _FakeMouse:
    def __init__(self):
        self.wheel_calls: list[tuple[int, int]] = []
        self.move_calls: list[tuple[int, int]] = []
        self.down_calls: int = 0
        self.up_calls: int = 0

    def wheel(self, dx: int, dy: int) -> None:
        self.wheel_calls.append((dx, dy))

    def move(self, x: int, y: int) -> None:
        self.move_calls.append((x, y))

    def down(self) -> None:
        self.down_calls += 1

    def up(self) -> None:
        self.up_calls += 1


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


def test_scroll_by_moves_mouse_before_wheeling_when_move_to_given():
    page = _FakePage()

    scroll_by(page, total_px=50, tick_px=100, tick_interval_ms=10, move_to=(640, 400))

    assert page.mouse.move_calls == [(640, 400)]
    assert [dy for _dx, dy in page.mouse.wheel_calls] == [50]


def test_scroll_by_does_not_move_mouse_when_move_to_omitted():
    page = _FakePage()

    scroll_by(page, total_px=50, tick_px=100, tick_interval_ms=10)

    assert page.mouse.move_calls == []


def test_drag_scroll_by_single_drag_when_total_smaller_than_step():
    page = _FakePage()

    drag_scroll_by(page, total_px=100, origin=(640, 700), drag_step_px=300, move_steps=5, step_delay_ms=1)

    assert page.mouse.down_calls == 1
    assert page.mouse.up_calls == 1
    # 起点への移動 + move_steps回の上方向移動 + 離す前の静止（同じ位置への移動）
    assert page.mouse.move_calls[0] == (640, 700)
    assert len(page.mouse.move_calls) == 1 + 5 + 1
    # 最後の移動は起点からtotal_pxぶん上（yが小さくなる）で、静止のため直前と同じ
    assert page.mouse.move_calls[-1] == (640, 600)
    assert page.mouse.move_calls[-2] == (640, 600)


def test_drag_scroll_by_splits_into_multiple_drags_when_total_exceeds_step():
    page = _FakePage()

    drag_scroll_by(page, total_px=700, origin=(640, 700), drag_step_px=300, move_steps=2, step_delay_ms=1)

    # 300 + 300 + 100 の3回に分けてdown/upが呼ばれる
    assert page.mouse.down_calls == 3
    assert page.mouse.up_calls == 3
