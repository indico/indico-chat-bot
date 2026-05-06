import pytest
from datetime import timedelta
from indico_chat_bot.bot import _parse_time_delta, _time_delta_to_string


@pytest.mark.parametrize(
    "text,expected_delta",
    [
        ("30m", timedelta(minutes=30)),
        ("2h", timedelta(hours=2)),
        ("7d", timedelta(days=7)),
        ("-2d", timedelta(days=-2)),
    ],
)
def test_time_delta_parsing(text, expected_delta):
    parsed_delta = _parse_time_delta(text)
    assert parsed_delta == expected_delta


@pytest.mark.parametrize(
    "delta,expected_text",
    [
        (timedelta(minutes=30), "30m"),
        (timedelta(hours=2), "2h"),
        (timedelta(days=7), "7d"),
        (timedelta(days=-2), "-2d"),
    ],
)
def test_time_delta_formatting(delta, expected_text):
    formatted_text = _time_delta_to_string(delta)
    assert formatted_text == expected_text
