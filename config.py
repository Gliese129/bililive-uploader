from utils import FileUtils


class GlobalConfig:
    min_size = 1
    max_size = 4
    process_dir: str
    delete_flag: bool
    port: int
    webhooks: list[str]
    account: dict

    def __init__(self, folder_path: str):
        config = FileUtils.YmlReader(folder_path + '\\global-config.yml')
        self.process_dir = config['recorder']['process-dir']
        self.delete_flag = config['recorder']['delete-after-upload']
        self.port = config['server']['port']
        self.webhooks = config['server']['webhooks']
        self.account = config['account']


class Condition:
    item: str
    regexp: str
    tags: list[str]
    upload: bool

    def __init__(self, item: str, regexp: str, tags: str, upload: bool):
        self.item = item
        self.regexp = regexp
        self.tags = tags.split(',')
        if upload is None:
            self.upload = upload
        else:
            self.upload = True


class Room:
    id: int
    tags: list[str]
    title: str
    description: str
    conditions: list[Condition]

    def __init__(self, room_id: int, tags: str, title: str, description: str, conditions: list[Condition]):
        self.id = room_id
        self.title = title
        self.description = description
        self.tags = tags.split(',')
        self.conditions = conditions


class RoomConfig:
    rooms: list[Room]

    def __init__(self, folder_path: str):
        config = FileUtils.YmlReader(folder_path + '\\room-config.yml')
        self.rooms = config['rooms']
