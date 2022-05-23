from backports.configparser import ConfigParser
from datetime import datetime
from pytz import timezone


def _split(text):
    return text.replace(" ", "").split(",")


def _process_bots(config):
    channel_ids = [
        section for section in config.sections() if section.startswith("channel_")
    ]
    bot_ids = [section for section in config.sections() if section.startswith("bot_")]
    channel_hooks = {cid[8:]: dict(config[cid]) for cid in channel_ids}
    bots = {}

    for bid in bot_ids:
        bot_data = config[bid]
        bot = {
            "nickname": bot_data["nickname"],
            "image_url": bot_data["image_url"],
            "categories": _split(bot_data["categories"]),
            "channels": _split(bot_data["channels"]),
            "timedelta": bot_data["timedelta"],
        }
        bots[bid[4:]] = bot

    return bots, channel_hooks


def read_config(config_file: str):
    config = ConfigParser()
    config.read(config_file)

    bots, channels = _process_bots(config)

    return {
        "storage_path": config.get("storage", "path", fallback="./storage.txt"),
        "server_url": config["indico"]["server_url"],
        "api_key": config.get("indico", "api_key", fallback=None),
        "secret": config.get("indico", "secret", fallback=None),
        "bots": bots,
        "channels": channels,
        "polling_time": int(config.get("bot", "polling_time", fallback="300")),
    }


def dt(dt_dict: dict):
    dt = datetime.combine(
        datetime.strptime(dt_dict["date"], "%Y-%m-%d"),
        datetime.strptime(dt_dict["time"], "%H:%M:%S").time(),
    )
    return timezone(dt_dict["tz"]).localize(dt)
