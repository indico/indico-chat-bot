import click
import json
import requests
import time
from configparser import ConfigParser
from datetime import timedelta, datetime
from pytz import timezone, utc
from urllib.parse import urlencode, urljoin


notified = set()


def _dt(dt_dict):
    dt = datetime.combine(datetime.strptime(dt_dict['date'], '%Y-%m-%d'),
                          datetime.strptime(dt_dict['time'], '%H:%M:%S').time())
    return timezone(dt_dict['tz']).localize(dt)


def _split(text):
    return text.replace(' ', '').split(',')


def _process_bots(config):
    channel_ids = [section for section in config.sections() if section.startswith('channel_')]
    bot_ids = [section for section in config.sections() if section.startswith('bot_')]
    channel_hooks = {cid[8:]: {'hook_url': config[cid]['hook_url'], 'text': config[cid]['text']} for cid in channel_ids}
    bots = {}

    for bid in bot_ids:
        bot_data = config[bid]
        bot = {
            'nickname': bot_data['nickname'],
            'image_url': bot_data['image_url'],
            'categories': _split(bot_data['categories']),
            'nickname': bot_data['nickname'],
            'channels': _split(bot_data['channels'])
        }
        bots[bid[4:]] = bot

    return bots, channel_hooks


def notify(event, bot, channels):
    for channel_id in bot['channels']:
        print(channels)
        channel = channels[channel_id]
        url = channel['hook_url']
        payload = {
            'text': channel['text'].format(**event),
            'nickname': bot['nickname'],
            'image_url': bot['image_url']
        }
        requests.post(url, data={'payload', json.dumps(payload)})


def read_config(config_file):
    config = ConfigParser()
    config.read(config_file)

    bots, channels = _process_bots(config)

    return {
        'server_url': config['indico']['server_url'],
        'api_key': config.get('indico', 'api_key', fallback=None),
        'secret': config.get('indico', 'secret', fallback=None),
        'bots': bots,
        'channels': channels
    }


def check_upcoming(config):
    global notified

    now = datetime.now(utc)

    bots, channels = config['bots'], config['channels']
    for bot in bots.values():
        url = urljoin(config['server_url'], 'export/categ/{}.json'.format('-'.join(bot['categories'])))
        qstring = urlencode({
            'from': 'now',
            'to': '+30m',
            'limit': 100
        })
        req = requests.get('{}?{}'.format(url, qstring))
        results = req.json()['results']

        for event in results:
            evt_id = event['id']
            start_dt = _dt(event['startDate'])
            if start_dt > (now - timedelta(hours=15)) and evt_id not in notified:
                notify(event, bot, channels)
                notified.add(evt_id)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
def run(config_file):
    config = read_config(config_file)
    while True:
        check_upcoming(config)
        time.sleep(60)


if __name__ == '__main__':
    cli()
