from datetime import datetime

from .utils import _setChannel

__all__ = ['LiveInfo', 'VideoInfo']


class LiveInfo:
    """

    Attributes:
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
    """

    Attributes:
        title: 视频标题
        videos: 视频列表
        description: 视频描述
        dynamic: 视频动态
        tid: 视频频道id
        tags: 视频标签
    """
    title: str
    videos: list[str]
    description: str
    dynamic: str
    tags: list[str]
    _channel: (str, str) = None
    channel = property(lambda self: self._channel, _setChannel)
    tid: int

    def __init__(self, room_config, videos: list[str]):
        self.videos = videos
        self.description = room_config.description
        self.tags = room_config.tags
        self.dynamic = room_config.dynamic
        self.title = room_config.title

    def tags_str(self) -> str:
        if len(self.tags) == 0:
            return ''
        return ','.join(self.tags)
