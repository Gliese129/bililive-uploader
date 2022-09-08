import logging
import os
from datetime import datetime

from sanic import Sanic

from entity import LiveInfo, RoomConfig, BotConfig
from utils import FileUtils

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')


class Process:
    """ class for process

    Attributes:
        folder: 录播文件所属文件夹
        origins: 原始文件名（不带后缀）
        videos: 处理后的文件名（不带后缀）
        live_info:
        room_config:
        bot_config:
    """
    folder: str
    origins: list[str]
    videos: list[str]
    live_info: LiveInfo
    room_config: RoomConfig

    def __init__(self, event_data: dict, room_config: RoomConfig):
        self.live_info = LiveInfo(event_data)
        self.origins, self.videos = [], []
        self.room_config = room_config
        self.live_info.read_start_time(app.config.TIME_CACHE_PATH, self.live_info.room_id)

    @staticmethod
    def session_start(room_id: int, start_time: datetime):
        rooms = FileUtils.readJson(app.config.TIME_CACHE_PATH)
        rooms[str(room_id)] = start_time.isoformat()
        FileUtils.writeDict(app.config.TIME_CACHE_PATH, rooms)

    @staticmethod
    def file_open(room_id: int, path: str):
        relative_folder, name = os.path.split(path)
        folder = os.path.join(app.ctx.bot_config.rec_dir, relative_folder)  # relative -> absolute
        name = os.path.splitext(name)[0]
        extensions = ['.flv', '.xml'] if app.ctx.bot_config.danmaku else ['.flv']
        for extension in extensions:  # check if file exists
            if not os.path.exists(os.path.join(folder, name + extension)):
                logger.warning(f'File "{name + extension}" should exist in folder "{folder}", but not found')

        rooms = FileUtils.readJson(app.config.VIDEO_CACHE_PATH)
        if str(room_id) not in rooms:
            rooms[str(room_id)] = {
                'folder': folder,
                'filenames': [],
                'extensions': extensions
            }
        rooms[str(room_id)]['filenames'].append(name)
        FileUtils.writeDict(app.config.VIDEO_CACHE_PATH, rooms)

    def live_end(self):
        pass
