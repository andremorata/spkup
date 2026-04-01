import pytest

from spkup.hotkey import HotkeyListener, parse_hotkey


@pytest.mark.parametrize(
    ("hotkey_str", "expected"),
    [
        ("ctrl+shift+space", ({"ctrl", "shift"}, "space")),
        ("alt+f1", ({"alt"}, "f1")),
        ("ctrl+space", ({"ctrl"}, "space")),
        ("space", (set(), "space")),
        ("shift+ctrl+space", ({"ctrl", "shift"}, "space")),
    ],
)
def test_parse_hotkey_valid_inputs(hotkey_str, expected):
    assert parse_hotkey(hotkey_str) == expected


@pytest.mark.parametrize(
    "hotkey_str",
    [
        "",
        "   ",
        "ctrl+shift",
        "hyper+space",
        "ctrl++space",
    ],
)
def test_parse_hotkey_invalid_inputs_raise_value_error(hotkey_str):
    with pytest.raises(ValueError):
        parse_hotkey(hotkey_str)


class _DummyKey:
    def __init__(self, *, char=None, name=None):
        self.char = char
        self.name = name


@pytest.fixture
def direct_invoke(monkeypatch):
    def _invoke_method(obj, method_name, connection_type):
        getattr(obj, method_name)()
        return True

    monkeypatch.setattr("spkup.hotkey.QMetaObject.invokeMethod", _invoke_method)


def test_hold_mode_stops_on_trigger_release(monkeypatch, direct_invoke):
    listener = HotkeyListener("ctrl+space")
    events = []
    listener.recording_started.connect(lambda: events.append("started"))
    listener.recording_stopped.connect(lambda: events.append("stopped"))

    times = iter([10.0, 10.5])
    monkeypatch.setattr("spkup.hotkey.time.monotonic", lambda: next(times))

    listener._on_press(_DummyKey(name="ctrl"))
    listener._on_press(_DummyKey(name="space"))
    listener._on_release(_DummyKey(name="space"))

    assert events == ["started", "stopped"]
    assert listener._is_active is False
    assert listener._toggle_mode is False


def test_quick_tap_enters_toggle_mode_and_second_combo_stops(monkeypatch, direct_invoke):
    listener = HotkeyListener("ctrl+space")
    events = []
    listener.recording_started.connect(lambda: events.append("started"))
    listener.recording_stopped.connect(lambda: events.append("stopped"))

    times = iter([20.0, 20.1])
    monkeypatch.setattr("spkup.hotkey.time.monotonic", lambda: next(times))

    listener._on_press(_DummyKey(name="ctrl"))
    listener._on_press(_DummyKey(name="space"))
    listener._on_release(_DummyKey(name="space"))

    assert events == ["started"]
    assert listener._is_active is True
    assert listener._toggle_mode is True

    listener._on_release(_DummyKey(name="ctrl"))
    listener._on_press(_DummyKey(name="ctrl"))
    listener._on_press(_DummyKey(name="space"))

    assert events == ["started", "stopped"]
    assert listener._is_active is False
    assert listener._toggle_mode is False
