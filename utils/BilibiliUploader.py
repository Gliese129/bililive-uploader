import logging
import os.path
import datetime
from bilibili_api import live, video_uploader, user
from utils import FileUtils
from config import Room, GlobalConfig

channel_data = './resources/channel.json'


class Uploader:
    credential: video_uploader.VideoUploaderCredential
    videos: list[str]
    description: str
    tags: str
    title: str
    parent_area: str
    child_area: str
    start_time: datetime
    room_id: int
    anchor: str

    def __init__(self, global_config: GlobalConfig, room_config: Room, videos: list[str],
                 parent_area: str, child_area: str, start_time: datetime, live_title: str,
                 room_id: int):
        self.credential = video_uploader.VideoUploaderCredential(account=global_config.account['username'],
                                                                 password=global_config.account['password'])
        self.videos = videos
        self.description = room_config.description
        self.tags = ','.join(room_config.tags)
        self.parent_area = parent_area
        self.child_area = child_area
        self.start_time = start_time
        self.set_title(title=room_config.title, live_title=live_title)
        self.room_id = room_id

    async def set_title(self, title: str, live_title: str):
        anchor = await self.get_anchor()
        self.anchor = anchor
        title.replace('${anchor}', anchor)
        title.replace('${title}', live_title)
        title.replace('${date}', self.start_time.strftime('%Y-%m-%d'))
        title.replace('${time}', self.start_time.strftime('%H:%M:%S'))
        title.replace('${parent_area}', self.parent_area)
        title.replace('${child_area}', self.child_area)
        self.title = title

    @staticmethod
    def set_pages(videos: list[str]) -> list[video_uploader.VideoUploaderPage]:
        pages = []
        for video in videos:
            page_info = {
                'video_stream': open(video, 'rb'),
                'title': video,
                'extension': 'flv'
            }
            page = video_uploader.VideoUploaderPage(**page_info)
            pages.append(page)
        return pages

    @staticmethod
    def fetch_channel(parent_area: str, child_area: str) -> int:
        logging.info('fetching channel...')
        channel = FileUtils.ReadJson(path=channel_data)
        tid = 0
        for main_ch in channel:
            if main_ch['name'] == parent_area:
                for sub_ch in main_ch['sub']:
                    if sub_ch['name'] == child_area:
                        tid = sub_ch['tid']
        logging.debug('parent area: %s   child area: %s  ->  channel id: %d' % (parent_area, child_area, tid))
        return tid

    async def get_anchor(self) -> str:
        live_room_api = live.LiveRoom(self.room_id)
        room_info = await live_room_api.get_room_info()
        uid = room_info.get('room_info').get('uid')
        user_api = user.User(uid)
        user_info = await user_api.get_user_info()
        anchor = user_info.get('name')
        return anchor

    async def upload(self):
        await self.credential.login()
        tid = self.fetch_channel(parent_area=self.parent_area, child_area=self.child_area)
        meta = {
            'copyright': 2,  # 投稿类型 1-自制，2-转载
            'source': 'https://live.bilibili.com/%d' % self.room_id,  # 视频来源。投稿类型为转载时注明来源，为原创时为空
            'desc': self.description,  # 视频简介
            'dynamic': '录播信息:\n开始时间: %s\n主播: %s' %
                       (self.start_time.strftime('%Y-%m-%d %H:%M:%S'), self.anchor),  # 动态信息
            'desc_format_id': 0,
            'open_elec': 0,  # 是否展示充电信息  1-是，0-否
            'no_reprint': 0,  # 显示未经作者授权禁止转载，仅当为原创视频时有效  1-启用，0-关闭
            'subtitles': {
                "lan": '',  # 字幕投稿语言，不清楚作用请将该项设置为空
                'open': 1  # 是否启用字幕投稿，1 or 0
                },
            'interactive': 0,
            'tag': self.tags,  # 视频标签。使用英文半角逗号分隔的标签组。示例：标签1,标签2,标签3
            'tid': tid,  # 分区ID。可以使用 channel 模块进行查询
            'title': self.title,  # 视频标题 【主播】 标题 时间
            'up_close_danmaku': False,  # 是否关闭弹幕
            'up_close_reply': False,  # 是否关闭评论
        }
        pages = self.set_pages(videos=self.videos)
        uploader = video_uploader.VideoUploader(pages=pages, meta=meta, credential=self.credential)
        logging.info('uploading...')
        logging.debug('file info:\ntitle: %s\ntid: %d\ntags: %s' % (self.title, tid, self.tags))
        ids = await uploader.start()
        logging.info('uploading finished, bvid=%s, aid=%s' % (ids['bvid'], ids['aid']))
