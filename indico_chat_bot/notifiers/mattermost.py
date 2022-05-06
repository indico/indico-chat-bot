import json
import requests


def notify(bot, channel, text):
    url = channel["hook_url"]
    payload = {"text": text, "username": bot["nickname"], "icon_url": bot["image_url"]}
    requests.post(url, data={b"payload": json.dumps(payload).encode("utf-8")})
