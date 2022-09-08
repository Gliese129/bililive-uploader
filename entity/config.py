import os.path
import functools
import re
from typing import Optional

from exceptions import *
from bilibili_api import Credential

from utils import FileUtils
from .info import LiveInfo
from .utils import _getValue, _setChannel

logger = logging.getLogger('bililive-uploader')
__all__ = ['BotConfig', 'RoomConfig']


class BotConfig:
    """

    Attributes:
        work_dir: 录播bot工作目录
        rec_dir: B站录播姬工作目录
        docker: 是否使用docker
        workers: 线程数
        danmaku: 是否压制弹幕
        multipart: 是否多p
        delete: 是否上传后删除
        auto_upload: 是否自动上传
        min_time: 录播最短时长
        port: 录播bot监听端口
        webhooks: webhook发送url
        credential: B站凭据
    """
    work_dir: str
    rec_dir: str
    docker: bool
    workers: int
    danmaku: bool
    multipart: bool
    delete: bool
    auto_upload: bool
    min_time: int
    port: int
    webhooks: list
    credential: Credential

    config_dir = property(lambda self: os.path.join(self.work_dir, 'config'))

    def __init__(self, work_dir: str):
        config = FileUtils.readYml(os.path.join(work_dir, 'config', 'global-config.yml'))
        get_value = functools.partial(_getValue, data=config)

        self.docker = get_value('bot/is-docker', False)
        if self.docker:
            self.rec_dir = '/record'
            self.work_dir = '/process'
            self.port = 8866
        else:
            self.rec_dir = get_value('bot/rec-dir')
            self.work_dir = work_dir
            self.port = get_value('bot/server/port', 8866)

        self.workers = get_value('bot/workers', 1)
        self.danmaku = get_value('bot/process/danmaku', True)
        self.multipart = get_value('bot/upload/multipart', False)
        self.delete = get_value('bot/upload/delete-after-upload', True)
        self.auto_upload = get_value('bot/upload/auto-upload', True)
        self.min_time = eval(str(get_value('bot/upload/min-time', 0)))

        self.webhooks = get_value('bot/server/webhooks', [])

        if self.auto_upload:
            credential = get_value('account/credential')
            self.credential = Credential(**credential)


class Condition:
    """ extra conditions for each room

    Attributes:
        item: 条件名称
        regexp: 正则表达式
        tags: 此条件下的上传标签
        channel: 此条件下的上传频道
        process: 此条件是否需要处理
    """
    item: str
    regexp: str
    tags: list[str]
    _channel: (str, str) = None
    channel = property(lambda self: self._channel, _setChannel)
    process: bool

    def __init__(self, config: dict):
        get_value = functools.partial(_getValue, data=config)
        self.item = get_value('item')
        self.regexp = str(get_value('regexp'))
        self.process = get_value('process', True)
        self.tags = get_value('tags', '').split(',')
        self.channel = config.get('channel', '')


class RoomConfig:
    """

    Attributes:
        id: 房间id, 长短号均可
        title: 视频标题(模板字符串)
        description: 视频描述(模板字符串)
        dynamic: 视频动态(模板字符串)
        channel: 上传频道
        tags: 上传标签
        conditions: 房间额外条件
    """
    id: int
    title: str
    description: str
    dynamic: str
    _channel: (str, str) = None
    channel = property(lambda self: self._channel, _setChannel)
    tags: list[str]
    conditions: list[Condition]

    def __init__(self, config: dict):
        default_desc = '本录播由@_Gliese_的脚本自动处理上传'
        get_value = functools.partial(_getValue, data=config)

        self.id = get_value('id')
        self.title = get_value('title', '{title}')
        self.description = get_value('description', default_desc)
        self.dynamic = get_value('dynamic', '')
        self.tags = get_value('tags', '').split(',')
        self.conditions = [Condition(c) for c in get_value('conditions', [])]
        self.channel = get_value('channel', '')

    @classmethod
    def init(cls, work_dir: str, room_id: int, short_id: int = 0) -> Optional['RoomConfig']:
        path = os.path.join(work_dir, 'config', 'room-config.yml')
        configs = FileUtils.readYml(path)
        for room in configs['rooms']:
            if int(room['id']) in (room_id, short_id):
                return cls(room)
        logger.warning('Unknown room: [id: %d] [short id: %d]', room_id, short_id)

    def list_conditions(self, live_info: LiveInfo) -> list[Condition]:
        """ list proper conditions

        :param live_info
        :return:
        """
        result = []
        for condition in self.conditions:
            try:
                if re.search(pattern=condition.regexp, string=getattr(live_info, condition.item)):
                    result.append(condition)
            except AttributeError as _:
                logger.warning('Invalid condition: %s', condition.item)
        return result
