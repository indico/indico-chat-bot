import click
import hashlib
import hmac
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
        channel = channels[channel_id]
        url = channel['hook_url']
        data = {
            'title': event['title'],
            'url': event['url'],
            'start_time': event['startDate']['time'][:5],
            'start_date': event['startDate']['date'],
            'start_tz': event['startDate']['tz'],
            'room': event['room'] if event['room'] else 'no room'
        }

        payload = {
            'text': channel['text'].format(**data),
            'username': bot['nickname'],
            'icon_url': bot['image_url']
        }
        requests.post(url, data={b'payload': json.dumps(payload).encode('utf-8')})


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


def check_upcoming(config, verbose):
    global notified

    now = datetime.now(utc)

    bots, channels = config['bots'], config['channels']
    for bot in bots.values():
        url = urljoin(config['server_url'], 'export/categ/{}.json'.format('-'.join(bot['categories'])))
        params = {
            'from': 'now',
            'to': '+30m',
            'limit': 100
        }
        if config['api_key']:
            params['api_key'] = config['api_key']
            if config['secret']:
                params['timestamp'] = str(int(time.time()))
                items = sorted(params.items(), key=lambda x: x[0].lower())
                param_url = '{}?{}'.format(url, urlencode(items)).encode('utf-8')
                params['signature'] = hmac.new(config['secret'].encode('utf-8'), param_url, hashlib.sha1).hexdigest()

        qstring = urlencode(params)
        url = '{}?{}'.format(url, qstring)
        if verbose:
            print('[d] URL: {}'.format(url))
        req = requests.get(url)
        results = req.json()['results']

        if verbose:
            print('[i] {} events found'.format(len(results)))

        for event in results:
            evt_id = event['id']
            start_dt = _dt(event['startDate'])
            if now > (start_dt - timedelta(minutes=15)) and start_dt > now and evt_id not in notified:
                notify(event, bot, channels)
                if verbose:
                    print('[>] Notified {} about {}'.format(bot['channels'], event['id']))
                notified.add(evt_id)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--verbose', default=False, is_flag=True)
def run(config_file, verbose):
    config = read_config(config_file)
    while True:
        if verbose:
            print('[i] Checking upcoming events')
        check_upcoming(config, verbose)
        time.sleep(60)


if __name__ == '__main__':
    cli()
