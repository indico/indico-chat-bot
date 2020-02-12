import os

from collections import defaultdict
from urllib.parse import urlparse

REDIS_AVAILABLE = False
try:
    # optional feature
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    pass

class Storage(object):
    _instance = None

    @classmethod
    def get_instance(cls, uri):
        if (not cls._instance):
            parsed = urlparse(uri)
            if parsed.scheme == 'file':
                cls._instance = TextStorage(parsed.netloc + parsed.path)
            elif parsed.scheme == 'redis':
                cls._instance = RedisStorage(uri)
            else:
                raise SystemError(f"Can't find scheme '{parsed.scheme}'")
            cls._instance.load()
        return cls._instance



class TextStorage(Storage):
    def __init__(self, path):
        print(path)
        self.path = path
        self.data = defaultdict(set)

    def load(self):
        if not os.path.exists(self.path):
            print(f"Storage file {self.path} didn't exist. Creating it...")
            self.save()
            print("Done")
        with open(self.path, 'r') as f:
            for line in f.readlines():
                if not line.strip():
                    continue
                bot_id, event_id = line.strip().split(' ')
                self.data[event_id].add(bot_id)

    def save(self):
        with open(self.path, 'w') as f:
            for event_id, bot_ids in self.data.items():
                for bot_id in bot_ids:
                    f.write(f'{bot_id} {event_id}\n')

    def has(self, key, value):
        return value in self.data[key]

    def add(self, key, value):
        self.data[key].add(value)


class RedisStorage(Storage):
    def __init__(self, uri):
        if not REDIS_AVAILABLE:
            raise RuntimeError("indico_chat_bot wasn't installed with redis support")
        self.redis = redis.Redis.from_url(uri)

    def load(self):
        # noop
        pass

    def save(self):
        # noop
        pass

    def has(self, key, value):
        return self.redis.sismember(key, value)

    def add(self, key, value):
        self.redis.sadd(key, value)
