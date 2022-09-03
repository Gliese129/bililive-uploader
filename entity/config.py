import os.path
import functools
from typing import Union, Optional

from exceptions import *
from bilibili_api import Credential

from utils import FileUtils


def _getValue(data: dict, path: str, default=None):
    """ get value from a dict
    if not exists, return default value when default is not None,
    otherwise throw ConfigNotCompleted exception

    :param data:
    :param path: in format of xx/xx/xx
    :param default:
    :return:
    """
    for p in path.split('/'):
        if p in data:
            data = data[p]
        elif default is not None:
            return default
        else:
            raise ConfigNotCompleted(path)
    return data


def _setChannel(self, data: Union[(str, str), str, list[str]]):
    if isinstance(data, tuple) and len(data) == 2:
        self._channel = data
    elif isinstance(data, list) and len(data) == 2:
        self._channel = tuple(data)
    elif isinstance(data, str) and len(data.split()) == 2:
        self._channel = tuple(data.split())
    else:
        self._channel = None


class BotConfig:
    """

    Attributes:
        work_dir: 录播bot工作目录
        rec_dir: B站录播姬工作目录
        docker: 是否使用docker
        workers: 线程数
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
    multipart: bool
    delete: bool
    auto_upload: bool
    min_time: int
    port: int
    webhooks: list
    credential: Credential

    config_dir = property(lambda self: os.path.join(self.work_dir, 'config'))

    def __init__(self, work_dir: str):
        config = FileUtils.readYml(os.path.join(self.config_dir, 'global-config.yml'))
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
    _channel: (str, str)
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
    _channel: (str, str)
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
    def init(cls, config_dir: str, room_id: int, short_id: int = 0) -> Optional['RoomConfig']:
        config = FileUtils.readYml(os.path.join(config_dir, 'room-config.yml'))
        return [cls(c) for c in config]



