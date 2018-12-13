import os

from collections import defaultdict


class Storage(defaultdict):
    _instance = None

    @classmethod
    def get_instance(cls, config):
        if (not cls._instance):
            cls._instance = cls(config)
            cls._instance.load()
        return cls._instance

    def __init__(self, config):
        super(Storage, self).__init__(set)
        self.path = config['storage_path']

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
                self[event_id].add(bot_id)

    def save(self):
        with open(self.path, 'w') as f:
            for event_id, bot_ids in self.items():
                for bot_id in bot_ids:
                    f.write(f'{bot_id} {event_id}\n')
