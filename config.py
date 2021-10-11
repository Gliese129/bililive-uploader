import os
from utils import FileUtils


class GlobalConfig:
    recorder_dir: str
    process_dir: str
    delete_flag: bool
    port: int
    webhooks: list[str]
    account: dict

    def __init__(self, folder_path: str):
        config = FileUtils.YmlReader(os.path.join(folder_path, 'global-config.yml'))
        self.recorder_dir = config['recorder']['recorder-dir']
        self.process_dir = config['recorder']['process-dir']
        self.delete_flag = config['recorder']['delete-after-upload']
        self.port = config['server']['port']
        self.webhooks = config['server']['webhooks']
        self.account = config['account']


class Condition:
    item: str
    regexp: str
    tags: list[str]
    process: bool

    def __init__(self, data: dict):
        self.item = data['item']
        self.regexp = str(data['regexp'])
        if data['tags'] is None:
            self.tags = []
        else:
            self.tags = data['tags'].split(',')
        if data['process'] is not None:
            self.process = data['process']
        else:
            self.process = True


class Room:
    id: int
    tags: list[str]
    title: str
    description: str
    conditions: list[Condition]

    def __init__(self, data: dict):
        self.id = data['id']
        self.title = data['title']
        self.description = data['description']
        self.tags = data['tags'].split(',')
        self.conditions = []
        for condition in data['conditions']:
            self.conditions.append(Condition(data=condition))


class RoomConfig:
    rooms: list[Room]

    def __init__(self, folder_path: str):
        config = FileUtils.YmlReader(os.path.join(folder_path, 'room-config.yml'))
        self.rooms = []
        for room in config['rooms']:
            self.rooms.append(Room(data=room))
