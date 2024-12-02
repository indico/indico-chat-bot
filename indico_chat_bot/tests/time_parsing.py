import unittest
from indico_chat_bot.bot import _parse_time_delta
from datetime import timedelta


class TimeParsingTests(unittest.TestCase):
    def test_time_delta_parsing(self):
        examples = {
            "minutes": "30m",
            "hours": "2h",
            "days": "7d",
        }

        expected = {
            "minutes": timedelta(minutes=30),
            "hours": timedelta(hours=2),
            "days": timedelta(days=7),
        }

        for time_unit, delta in examples.items():
            parsed_delta = _parse_time_delta(delta)
            expected_result = expected[time_unit]
            self.assertEqual(parsed_delta, expected_result)


if __name__ == "__main__":
    unittest.main()
