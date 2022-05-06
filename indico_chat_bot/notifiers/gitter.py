import requests


def notify(bot, channel, text):
    url = channel["hook_url"]
    payload = {"message": text, "level": channel.get("level", "info")}
    requests.post(url, json=payload)
