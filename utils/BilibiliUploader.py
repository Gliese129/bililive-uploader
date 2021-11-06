# -*- coding: utf-8 -*-
import asyncio
import logging
import datetime
import warnings

from bilibili_api import live, video_uploader, user
from utils import FileUtils
from config import Room, GlobalConfig

channel_data = './resources/channel.json'


class Uploader:
    credential: video_uploader.Credential
    videos: list[str]
    description: str
    tags: str
    title: str
    live_title: str
    parent_area: str
    child_area: str
    start_time: datetime
    room_id: int
    anchor: str
    dynamic: str

    def __init__(self, access_key: dict, room_config: Room, videos: list[str],
                 parent_area: str, child_area: str, start_time: datetime, live_title: str,
                 room_id: int, session_id: str, origin_videos: list[str]):
        self.credential = video_uploader.Credential(**access_key)
        self.videos = videos
        self.description = room_config.description
        self.dynamic = room_config.dynamic
        self.tags = ','.join(room_config.tags)
        self.parent_area = parent_area
        self.child_area = child_area
        self.start_time = start_time
        self.title = room_config.title
        self.live_title = live_title
        self.room_id = room_id

    def set_module(self, module_string: str) -> str:
        """
        设置模板
        :param module_string: 模板字符串
        :return: 替换后的结果
        """
        return module_string.replace('${anchor}', self.anchor) \
            .replace('${title}', self.live_title) \
            .replace('${date}', self.start_time.strftime('%Y-%m-%d')) \
            .replace('${time}', self.start_time.strftime('%H:%M:%S')) \
            .replace('${parent_area}', self.parent_area) \
            .replace('${child_area}', self.child_area)

    @staticmethod
    def set_pages(videos: list[str]) -> list[video_uploader.VideoUploaderPage]:
        """
        分页设置
        :param videos: 视频列表
        :return: 分页
        """
        pages = []
        index = 1
        for video in videos:
            page_info = {
                'path': video,
                'title': f'part{index}',
                'description': ''
            }
            page = video_uploader.VideoUploaderPage(**page_info)
            pages.append(page)
            index += 1
        return pages

    @staticmethod
    def fetch_channel(parent_area: str, child_area: str) -> int:
        """
        获取分区id
        :param parent_area: 父区域
        :param child_area: 子区域
        :return: 分区id
        """
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
        """
        获取主播姓名
        :return: 主播姓名
        """
        live_room_api = live.LiveRoom(self.room_id)
        room_info = await live_room_api.get_room_info()
        uid = room_info.get('room_info').get('uid')
        user_api = user.User(uid)
        user_info = await user_api.get_user_info()
        anchor = user_info.get('name')
        return anchor

    async def upload(self) -> bool:
        """
        上传视频
        :return: 是否上传成功
        """
        success = False
        self.anchor = await self.get_anchor()
        self.title = self.set_module(module_string=self.title)
        self.description = self.set_module(module_string=self.description)
        self.dynamic = self.set_module(module_string=self.dynamic)
        try:
            tid = self.fetch_channel(parent_area=self.parent_area, child_area=self.child_area)
            meta = {
                'copyright': 2,  # 投稿类型 1-自制，2-转载
                'source': 'https://live.bilibili.com/%d' % self.room_id,  # 视频来源。投稿类型为转载时注明来源，为原创时为空
                'desc': self.description,  # 视频简介
                'dynamic': self.dynamic,  # 视频动态
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
            for page in pages:
                uploader = video_uploader.VideoUploader(pages=[page], meta=meta, credential=self.credential)
                logging.info('uploading...')
                logging.debug('file info:\ntitle: %s\ntid: %d\ntags: %s' % (self.title, tid, self.tags))
                ids = await uploader.start()
                logging.info('uploading finished, bvid=%s, aid=%s' % (ids['bvid'], ids['aid']))
            success = True
        except Exception as e:
            logging.error(e)
        finally:
            return success
