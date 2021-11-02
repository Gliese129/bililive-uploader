import os
from utils import FileUtils


class GlobalConfig:
    recorder_dir: str
    process_dir: str
    delete_flag: bool
    port: int
    webhooks: list[str]
    account: dict
    isDocker: bool

    def __init__(self, folder_path: str):
        config = FileUtils.YmlReader(os.path.join(folder_path, 'global-config.yml'))
        self.isDocker = False if config['recorder']['is-docker'] is None else config['recorder']['is-docker']
        if self.isDocker:
            self.recorder_dir = '/recorder'
            self.process_dir = '/process'
            self.port = 8866
        else:
            self.recorder_dir = config['recorder']['recorder-dir']
            self.process_dir = config['recorder']['process-dir']
            self.port = config['server']['port']
        self.delete_flag = False if config['recorder']['delete-after-upload'] is None \
            else config['recorder']['delete-after-upload']
        self.webhooks = [] if config['server']['webhooks'] is None else config['server']['webhooks']
        self.account = config['account']


class Condition:
    item: str
    regexp: str
    tags: list[str]
    process: bool

    def __init__(self, data: dict):
        self.item = data['item']
        self.regexp = str(data['regexp'])
        self.tags = [] if data['tags'] is None else data['tags'].split(',')
        self.process = True if data['process'] is None else data['process']


class Room:
    id: int
    tags: list[str]
    title: str
    description: str
    conditions: list[Condition]

    def __init__(self, data: dict):
        self.id = data['id']
        self.title = data['title']
        default_desc = '本录播由@_Gliese_的脚本自动处理上传data'
        self.description = default_desc if data['description'] is None else data['description']
        self.tags = [] if data['tags'] is None else data['tags'].split(',')
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
