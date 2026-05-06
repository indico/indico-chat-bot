import requests


def notify(bot, channel, text):
    url = channel['hook_url']
    payload = {'text': text, 'username': bot['nickname'], 'icon_url': bot['image_url']}
    requests.post(url, json=payload)
