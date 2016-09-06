import click
import hashlib
import hmac
import json
import re
import requests
import time
from configparser import ConfigParser
from datetime import datetime, timedelta
from pytz import timezone, utc
from urllib.parse import urlencode, urljoin


notified = set()


def _parse_time_delta(time_delta):
    """
    Parse string and return a timedelta.

    Accepted formats:

     * days in the future/past: '[+/-]DdHHhMMm'
    """
    m = re.match(r'^([+-])?(?:(\d{1,3})d)?(?:(\d{1,2})h)?(?:(\d{1,2})m)?$', time_delta)
    if m:
        mod = -1 if m.group(1) == '-' else 1

        atoms = list(0 if a is None else int(a) * mod for a in m.groups()[1:])
        if atoms[1] > 23 or atoms[2] > 59:
            raise Exception("Invalid time!")
        return timedelta(days=atoms[0], hours=atoms[1], minutes=atoms[2])
    else:
        raise Exception("Wrong format for timedelta: %s" % time_delta)


def _dt(dt_dict):
    dt = datetime.combine(datetime.strptime(dt_dict['date'], '%Y-%m-%d'),
                          datetime.strptime(dt_dict['time'], '%H:%M:%S').time())
    return timezone(dt_dict['tz']).localize(dt)


def _split(text):
    return text.replace(' ', '').split(',')


def _process_bots(config):
    channel_ids = [section for section in config.sections() if section.startswith('channel_')]
    bot_ids = [section for section in config.sections() if section.startswith('bot_')]
    channel_hooks = {cid[8:]: {'hook_url': config[cid]['hook_url'],
                               'text': config[cid]['text']}
                     for cid in channel_ids}
    bots = {}

    for bid in bot_ids:
        bot_data = config[bid]
        bot = {
            'nickname': bot_data['nickname'],
            'image_url': bot_data['image_url'],
            'categories': _split(bot_data['categories']),
            'nickname': bot_data['nickname'],
            'channels': _split(bot_data['channels']),
            'timedelta': bot_data['timedelta']
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


def _is_fetching_past_events(bot):
    return bot['timedelta'].startswith('-')


def check_upcoming(config, verbose):
    global notified

    now = datetime.now(utc)

    bots, channels = config['bots'], config['channels']
    for bot in bots.values():
        url_path = 'export/categ/{}.json'.format('-'.join(bot['categories']))
        params = {
            'from': 'now',
            'to': bot['timedelta'],
            'limit': '100'
        }
        if _is_fetching_past_events(bot):
            time_delta = _parse_time_delta(bot['timedelta'])
            from_date = now + time_delta
            params['from'] = (from_date - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
            params['to'] = from_date.strftime("%Y-%m-%dT%H:%M")
            params['tz'] = 'UTC'

        if config['api_key']:
            params['apikey'] = config['api_key']
            if config['secret']:
                params['timestamp'] = str(int(time.time()))
                items = sorted(params.items(), key=lambda x: x[0].lower())
                param_url = '/{}?{}'.format(url_path, urlencode(items)).encode('utf-8')
                params['signature'] = hmac.new(config['secret'].encode('utf-8'), param_url, hashlib.sha1).hexdigest()

        qstring = urlencode(params)
        url = '{}?{}'.format(urljoin(config['server_url'], url_path), qstring)
        if verbose:
            print('[d] URL: {}'.format(url))
        req = requests.get(url)
        results = req.json()['results']

        if verbose:
            print('[i] {} events found'.format(len(results)))

        for event in results:
            evt_id = event['id']
            start_dt = _dt(event['startDate'])
            if (_is_fetching_past_events(bot) or start_dt > now) and evt_id not in notified:
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
