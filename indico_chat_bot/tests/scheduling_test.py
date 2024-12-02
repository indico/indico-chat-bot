import pytest
from collections import defaultdict
from pytz import timezone

from ..bot import check_upcoming
from ..storage import Storage
from ..util import dt


ZURICH_TZ = timezone("Europe/Zurich")
CONFIG = {
    "bots": {
        "bot_1": {"timedelta": "1h", "categories": "1", "channels": (1,)},
        "bot_2": {"timedelta": "1d", "categories": "2", "channels": (1,)},
    },
    "channels": {1: {"text": "Whatever"}},
}

CATEGORIES = {
    "1": (
        {
            "id": 1,
            "startDate": {
                "date": "2022-06-07",
                "time": "10:00:00",
                "tz": "Europe/Zurich",
            },
            "title": "Event 1",
            "url": "https://events/1",
            "room": "Room 1",
        },
        {
            "id": 2,
            "startDate": {
                "date": "2022-06-07",
                "time": "10:30:00",
                "tz": "Europe/Zurich",
            },
            "title": "Event 2",
            "url": "https://events/2",
            "room": "Room 1",
        },
    ),
    "2": (
        {
            "id": 3,
            "startDate": {
                "date": "2022-06-08",
                "time": "17:00:00",
                "tz": "Europe/Zurich",
            },
            "title": "Event 3",
            "url": "https://events/3",
            "room": "Room 1",
            "label": None,
        },
        {
            "id": 4,
            "startDate": {
                "date": "2022-06-08",
                "time": "17:30:00",
                "tz": "Europe/Zurich",
            },
            "title": "Event 4",
            "url": "https://events/4",
            "room": "Room 1",
            "label": None,
        },
        {
            "id": 5,
            "startDate": {
                "date": "2022-06-07",
                "time": "17:30:00",
                "tz": "Europe/Zurich",
            },
            "title": "Event 5",
            "url": "https://events/5",
            "room": "Room 1",
            "label": {"is_event_not_happening": True},
        },
    ),
}


class DummyStorage(Storage):
    def __init__(self):
        self.data = defaultdict(set)

    def load(self):
        # noop
        pass

    def save(self):
        # noop
        pass

    def has(self, key, value):
        return value in self.data[key]

    def add(self, key, value):
        self.data[key].add(value)


def dummy_fetcher(categ_list, now, time_delta, config, debug=False) -> list:
    res = []
    for categ_id in categ_list:
        for event in CATEGORIES[categ_id]:
            event_start_dt = dt(event["startDate"])
            if (now < event_start_dt and event_start_dt <= (now + time_delta)) or (
                now > event_start_dt and event_start_dt >= (now + time_delta)
            ):
                res.append(event)
    return res


@pytest.mark.freeze_time("2022-06-07 06:59")
def test_no_upcoming():
    upcoming = list(
        r[0]
        for r in check_upcoming(
            CONFIG,
            DummyStorage(),
            False,
            dummy_fetcher,
        )
    )
    assert not {e["id"] for e in upcoming}


@pytest.mark.freeze_time("2022-06-07 07:00")
def test_one_upcoming():
    upcoming = list(
        r[0]
        for r in check_upcoming(
            CONFIG,
            DummyStorage(),
            False,
            dummy_fetcher,
        )
    )
    assert {e["id"] for e in upcoming} == {1}


@pytest.mark.freeze_time("2022-06-07 07:30")
def test_two_upcoming():
    upcoming = list(
        r[0]
        for r in check_upcoming(
            CONFIG,
            DummyStorage(),
            False,
            dummy_fetcher,
        )
    )
    assert {e["id"] for e in upcoming} == {1, 2}


@pytest.mark.freeze_time("2022-06-07 15:00")
def test_one_upcoming_day():
    upcoming = list(
        r[0]
        for r in check_upcoming(
            CONFIG,
            DummyStorage(),
            False,
            dummy_fetcher,
        )
    )
    assert {e["id"] for e in upcoming} == {3}


@pytest.mark.freeze_time("2022-06-07 15:30")
def test_two_upcoming_day():
    upcoming = list(
        r[0]
        for r in check_upcoming(
            CONFIG,
            DummyStorage(),
            False,
            dummy_fetcher,
        )
    )
    assert {e["id"] for e in upcoming} == {3, 4}
