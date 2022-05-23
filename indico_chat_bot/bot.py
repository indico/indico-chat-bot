import atexit
import hashlib
import hmac
import re
import os
import sys
import time
import typing as t
from datetime import datetime, timedelta

import click
import requests
from loguru import logger
from pytz import utc
from urllib.parse import urlencode, urljoin

from . import notifiers
from .util import read_config, dt
from .storage import Storage
from .exceptions import InvalidTimeDeltaFormat, InvalidTime, UnknownNotifier


LOGGER_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS!UTC}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


def _parse_time_delta(time_delta: str) -> timedelta:
    """
    Parse string and return a timedelta.

    Accepted formats:

     * days in the future/past: '[+/-]DdHHhMMm'
    """
    m = re.match(r"^([+-])?(?:(\d{1,3})d)?(?:(\d{1,2})h)?(?:(\d{1,2})m)?$", time_delta)
    if m:
        mod = -1 if m.group(1) == "-" else 1

        atoms = list(0 if a is None else int(a) * mod for a in m.groups()[1:])
        if atoms[1] > 23 or atoms[2] > 59:
            raise InvalidTime()
        return timedelta(days=atoms[0], hours=atoms[1], minutes=atoms[2])
    else:
        raise InvalidTimeDeltaFormat(time_delta)


def _time_delta_to_string(time_delta: timedelta) -> str:
    # https://stackoverflow.com/a/49226644
    res = "-" if time_delta.days < 0 else ""
    secs = int(abs(time_delta).total_seconds())

    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        res += f"{days}d"
    if hours:
        res += f"{hours}h"
    if minutes:
        res += f"{minutes}m"
    return res


def notify(event, bot, channels):
    """Notify a list of channels about an event."""
    for channel in channels:
        data = {
            "title": event["title"],
            "url": event["url"],
            "start_time": event["startDate"]["time"][:5],
            "start_date": event["startDate"]["date"],
            "start_tz": event["startDate"]["tz"],
            "room": event["room"] if event["room"] else "no room",
        }
        text = channel["text"].format(**data)

        channel_type = channel.get("type")
        if channel_type not in notifiers.ALL_NOTIFIERS:
            raise UnknownNotifier(channel_type)

        logger.info(
            f"Notifying channel '{channel['hook_url']}' about event '{event['title']}' ({event['id']})"
        )
        getattr(notifiers, channel_type).notify(bot, channel, text)


def fetch_indico_categories(
    categ_list: t.List[str],
    now: datetime,
    time_delta: timedelta,
    config: dict,
    debug: bool = False,
) -> dict:
    url_path = "export/categ/{}.json".format("-".join(categ_list))
    params = {"from": "now", "to": _time_delta_to_string(time_delta), "limit": "100"}

    if debug:
        params["nc"] = "yes"

    # time delta is negative (send alarm after event, not before)
    if time_delta < timedelta():
        from_date = now + time_delta
        params["from"] = (from_date - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        params["to"] = from_date.strftime("%Y-%m-%dT%H:%M")
        params["tz"] = "UTC"

    if config["api_key"]:
        params["apikey"] = config["api_key"]
        if config["secret"]:
            params["timestamp"] = str(int(time.time()))
            items = sorted(params.items(), key=lambda x: x[0].lower())
            param_url = "/{}?{}".format(url_path, urlencode(items)).encode("utf-8")
            params["signature"] = hmac.new(
                config["secret"].encode("utf-8"), param_url, hashlib.sha1
            ).hexdigest()

    qstring = urlencode(params)
    url = "{}?{}".format(urljoin(config["server_url"], url_path), qstring)
    logger.debug("URL: {}".format(url))
    req = requests.get(url, verify=(not debug))
    return req.json()["results"]


def check_upcoming(
    config: dict,
    storage: Storage,
    debug: bool,
    fetcher=fetch_indico_categories,
):
    bots, channels = config["bots"], config["channels"]
    now = datetime.now(utc)

    for bot_id, bot in bots.items():
        time_delta = _parse_time_delta(bot["timedelta"])
        results = fetcher(bot["categories"], now, time_delta, config, debug=debug)

        logger.info("{} events found".format(len(results)))

        for event in results:
            evt_id = event["id"]
            start_dt = dt(event["startDate"])

            event_time_delta_minutes = (start_dt - now).total_seconds() / 60
            bot_time_delta_minutes = time_delta.total_seconds() / 60

            time_delta_satisfied = (
                0 < event_time_delta_minutes <= bot_time_delta_minutes
            )
            in_storage = storage.has(evt_id, bot_id)

            logger.debug(
                f" - {evt_id} | delta: {time_delta} | within_delta: {time_delta_satisfied} | storage: {in_storage}"
            )

            if (time_delta < timedelta() or time_delta_satisfied) and not in_storage:
                yield event, bot, (channels[cid] for cid in bot["channels"])
                logger.debug(f"Adding event {evt_id} to storage")
                storage.add(evt_id, bot_id)


@click.group()
def cli():
    pass


def _save_storage(storage):
    print("Saving storage... ")
    storage.save()
    print("Done!")


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--verbose", default=False, is_flag=True)
@click.option("--debug", default=False, is_flag=True)
def run(config_file, verbose, debug):
    config = read_config(config_file)
    storage = Storage.get_instance(config["storage_path"])

    env_debug = os.environ.get("DEBUG")
    if env_debug:
        debug = env_debug == "1"

    if debug:
        log_level = "DEBUG"
    elif verbose:
        log_level = "INFO"
    else:
        log_level = "WARNING"

    logger.remove()
    logger.add(
        sys.stderr,
        format=LOGGER_FORMAT,
        filter="indico_chat_bot",
        colorize=True,
        level=log_level
    )

    atexit.register(lambda: _save_storage(storage))

    polling_time = config["polling_time"]

    while True:
        logger.info("Checking upcoming events")
        for event, bot, channels in check_upcoming(config, storage, debug):
            notify(event, bot, channels)
            logger.info("Notified {} about {}".format(bot["channels"], event["id"]))
        logger.info(
            f"Sleeping till {datetime.utcnow() + timedelta(seconds=polling_time)}..."
        )
        time.sleep(polling_time)


if __name__ == "__main__":
    cli()
