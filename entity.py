import logging
import os
import re
from datetime import datetime
from utils import FileUtils


class LiveInfo:
    pass


class GlobalConfig:
    """ 录播bot配置

    Fields:
        recorder_dir: B站录播姬工作目录
        process_dir: 录播bot工作目录
        delete_flag: 是否上传后删除
        port: 录播bot监听端口
        webhooks: webhook发送url
        isDocker: 是否使用docker运行
    """
    recorder_dir: str
    process_dir: str
    delete_flag: bool
    port: int
    webhooks: list[str]
    isDocker: bool
    workers: int
    multipart: bool

    def __init__(self, folder_path: str):
        config = FileUtils.YmlReader(os.path.join(folder_path, 'global-config.yml'))
        self.isDocker = config['recorder']['is-docker'] if config['recorder'].get('is-docker') is not None else False
        self.workers = config['recorder']['workers'] if config['recorder'].get('workers') is not None else 32
        if self.isDocker:
            self.recorder_dir = '/recorder'
            self.process_dir = '/process'
            self.port = 8866
        else:
            self.recorder_dir = config['recorder']['recorder-dir']
            self.process_dir = config['recorder']['process-dir']
            self.port = config['server']['port']
        self.delete_flag = config['recorder']['delete-after-upload'] \
            if config['recorder'].get('delete-after-upload') is not None else False
        self.webhooks = config['server']['webhooks'] if config['server'].get('webhooks') is not None else []
        self.multipart = config['recorder']['multipart'] if config['recorder'].get('multipart') is not None else False


class Condition:
    """ 房间额外条件配置

    Fields:
        item: 条件名称
        regexp: 正则表达式
        tags: 此条件下的上传标签
        channel: 此条件下的上传频道
        process: 此条件是否需要处理
    """
    item: str
    regexp: str
    tags: list[str]
    channel: (str, str)
    process: bool

    def __init__(self, data: dict):
        self.item = data['item']
        self.regexp = str(data['regexp'])
        self.tags = data['tags'].split(',') if data.get('tags') is not None else []
        self.process = data['process'] if data.get('process') is not None else True
        if data.get('channel') is not None:
            channels = data['channel'].split('')
            self.channel = (channels[0], channels[1]) if len(channels) == 2 else None
        else:
            self.channel = None


class RoomConfig:
    """ 房间配置

    Fields:
        id: 房间id, 长短号均可
        tags: 上传标签
        channel: 上传频道
        title: 视频标题(模板字符串)
        description: 视频描述(模板字符串)
        dynamic: 视频动态(模板字符串)
        conditions: 房间额外条件
    """
    id: int
    tags: list[str]
    channel: (str, str)
    title: str
    description: str
    dynamic: str
    conditions: list[Condition]

    def __init__(self, data: dict):
        default_desc = '本录播由@_Gliese_的脚本自动处理上传'

        self.id = data['id']
        self.title = data['title']
        self.description = data['description'] if data.get('description') is not None else default_desc
        self.dynamic = data['dynamic'] if data.get('dynamic') is not None else ''
        self.tags = data['tags'].split(',') if data.get('tags') is not None else []
        self.conditions = []
        if data.get('conditions') is not None:
            for condition in data['conditions']:
                self.conditions.append(Condition(condition))
        if data.get('channel') is not None:
            channels = data['channel'].split(' ')
            self.channel = (channels[0], channels[1]) if len(channels) == 2 else None
        else:
            self.channel = None

    @classmethod
    def get_config(cls, folder_path: str, room_id: int, short_id: int = None):
        configs = FileUtils.YmlReader(os.path.join(folder_path, 'room-config.yml'))
        for room in configs['rooms']:
            config = cls(room)
            if config.id == room_id or config.id == short_id:
                return config
        return None

    def list_proper_conditions(self, live_info: LiveInfo) -> list[Condition]:
        """ 返回符合条件的额外条件

        :param live_info: 直播信息
        :return: 符合条件的额外条件
        """
        conditions = []
        for condition in self.conditions:
            try:
                if re.search(pattern=condition.regexp, string=live_info.__getattribute__(condition.item)):
                    conditions.append(condition)
            except AttributeError as e:
                logging.error(e)
        return conditions

    def set_channel(self, channel_str: str) -> None:
        """ 设置频道

        :param channel_str: 频道(空格分割)
        """
        channels = channel_str.split(' ')
        if len(channels) == 2:
            self.channel = (channels[0], channels[1])


class LiveInfo:
    """ 直播信息

    Fields:
        room_id: 直播间长号
        short_id: 直播间短号
        anchor: 主播
        title: 直播间标题
        start_time: 开始时间
        parent_area: 父区域
        child_area: 子区域
        session_id: 会话id
    """
    room_id: int
    short_id: int
    anchor: str
    title: str
    start_time: datetime
    parent_area: str
    child_area: str
    session_id: str

    def __init__(self, event_data: dict):
        self.room_id = event_data['RoomId']
        self.short_id = event_data['ShortId']
        self.title = event_data['Title']
        self.session_id = event_data['SessionId']
        self.parent_area = event_data['AreaNameParent']
        self.child_area = event_data['AreaNameChild']
        self.anchor = event_data['Name']


class VideoInfo:
    """ 视频信息

    Fields:
        tags: 视频标签
        description: 视频描述
        dynamic: 视频动态
        title: 视频标题
        tid: 视频频道id
    """
    tags: list[str]
    description: str
    dynamic: str
    title: str
    tid: int
    channel: (str, str)

    def __init__(self, room_config: RoomConfig):
        self.description = room_config.description
        self.tags = room_config.tags
        self.dynamic = room_config.dynamic
        self.title = room_config.title

    def get_tags(self) -> str:
        if len(self.tags) == 0:
            return ''
        return ','.join(self.tags)
