import pytest

from spkup.hotkey import parse_hotkey


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
