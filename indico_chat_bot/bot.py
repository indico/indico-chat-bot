import atexit
import hashlib
import hmac
import json
import re
import os
import sys
import time
from datetime import datetime, timedelta

import click
import requests
from pytz import timezone, utc
from urllib.parse import urlencode, urljoin

from . import notifiers
from .util import read_config
from .storage import Storage



def _info(message):
    print(message)
    sys.stdout.flush()


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


def _is_fetching_past_events(bot):
    return bot['timedelta'].startswith('-')


def notify(event, bot, channels):
    for channel_id in bot['channels']:
        channel = channels[channel_id]
        data = {
            'title': event['title'],
            'url': event['url'],
            'start_time': event['startDate']['time'][:5],
            'start_date': event['startDate']['date'],
            'start_tz': event['startDate']['tz'],
            'room': event['room'] if event['room'] else 'no room'
        }
        text = channel['text'].format(**data)

        channel_type = channel.get('type')
        if channel_type not in notifiers.ALL_NOTIFIERS:
            raise SystemError(f"Unkown notifier '{channel_type}'")
        getattr(notifiers, channel_type).notify(bot, channel, text)


def check_upcoming(config, storage, verbose, debug):
    now = datetime.now(utc)

    bots, channels = config['bots'], config['channels']
    for bot_id, bot in bots.items():
        url_path = 'export/categ/{}.json'.format('-'.join(bot['categories']))
        params = {
            'from': 'now',
            'to': bot['timedelta'],
            'limit': '100'
        }

        if debug:
            verbose = True
            params['nc'] = 'yes'

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
            _info('[d] URL: {}'.format(url))
        req = requests.get(url, verify=(not debug))
        results = req.json()['results']

        if verbose:
            _info('[i] {} events found'.format(len(results)))

        for event in results:
            evt_id = event['id']
            start_dt = _dt(event['startDate'])
            if (_is_fetching_past_events(bot) or start_dt > now) and not storage.has(evt_id, bot_id):
                notify(event, bot, channels)
                if verbose:
                    _info('[>] Notified {} about {}'.format(bot['channels'], event['id']))
                storage.add(evt_id, bot_id)


@click.group()
def cli():
    pass


def _save_storage(storage):
    print(f"Saving storage... ")
    storage.save()
    print("Done!")


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--verbose', default=False, is_flag=True)
@click.option('--debug', default=False, is_flag=True)
def run(config_file, verbose, debug):
    config = read_config(config_file)
    storage = Storage.get_instance(config['storage_path'])

    atexit.register(lambda: _save_storage(storage))

    env_debug = os.environ.get('DEBUG')
    if env_debug:
        debug = env_debug == '1'

    while True:
        if verbose:
            _info('[i] Checking upcoming events')
        check_upcoming(config, storage, verbose, debug)
        time.sleep(config['polling_time'])


if __name__ == '__main__':
    cli()
