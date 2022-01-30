# -*- coding: utf-8 -*-
import asyncio
import logging
import os

from bilibili_api import video_uploader, Credential
from utils import FileUtils
from entity import RoomConfig, LiveInfo, VideoInfo
from utils.FileUtils import ReadJson

channel_data = './resources/channel.json'
live_to_video_data = './config/live-to-video.json'


class Uploader:
    credential: video_uploader.Credential
    videos: list[str]
    room_id: int
    live_info: LiveInfo
    video_info: VideoInfo
    room_config: RoomConfig
    channel: (str, str)

    def __init__(self, credential: Credential, room_config: RoomConfig, videos: list[str], live_info: LiveInfo, **unused):
        self.credential = credential
        self.videos = videos
        self.video_info = VideoInfo(room_config=room_config)
        self.room_config = room_config
        self.live_info = live_info
        self.room_id = live_info.room_id

    @staticmethod
    def get_channel(channel: str) -> (str, str):
        """ 将分区字符串转为元组

        :param channel 分区(父分区和子分区由空格分割)
        :return: 分区元组
        """
        parent_area, child_area = channel.split(' ')
        return parent_area, child_area

    def set_module(self, module_string: str) -> str:
        """ 设置模板

        :param module_string: 模板字符串
        :return: 替换后的结果
        """
        live_info = self.live_info
        return module_string.replace('${anchor}', live_info.anchor) \
            .replace('${title}', live_info.title) \
            .replace('${date}', live_info.start_time.strftime('%Y-%m-%d')) \
            .replace('${time}', live_info.start_time.strftime('%H:%M:%S')) \
            .replace('${parent_area}', live_info.parent_area) \
            .replace('${child_area}', live_info.child_area)

    def set_tags_and_channel(self) -> None:
        """ 设置标签和分区

        :return: None
        """
        # 先在room_config中设置channel和tags
        self.video_info.channel = self.room_config.channel
        self.video_info.tags = self.room_config.tags
        # 在live-to-video中查找channel，查到则直接替换
        live_to_video = ReadJson(path=live_to_video_data)
        for parent_area in live_to_video:
            flag = False
            if parent_area.get('name') == self.live_info.parent_area:
                # 直播父分区可以直接对应频道
                if parent_area.get('channel') is not None:
                    channel = self.get_channel(parent_area.get('channel'))
                    if channel is not None:
                        self.video_info.channel = channel
                        flag = True
                # 直播父分区无法直接对应，查找子分区
                elif parent_area.get('children') is not None:
                    for child_area in parent_area.get('children'):
                        if child_area.get('name') == self.live_info.child_area:
                            # 子分区可以直接对应频道
                            if child_area.get('channel') is not None:
                                channel = self.get_channel(child_area.get('channel'))
                                if channel is not None:
                                    self.video_info.channel = channel
                                    flag = True
                                    break
                if flag:
                    break
        # 最后在condition中查找channel，追加tags
        conditions = self.room_config.list_proper_conditions(live_info=self.live_info)
        for condition in conditions:
            self.video_info.tags.extend(condition.tags)
            if condition.channel is not None:
                self.video_info.channel = condition.channel
        if self.video_info.channel is None:
            logging.info(f'[{self.live_info.room_id}] {self.live_info.parent_area}-{self.live_info.child_area} -> ?')
            raise Exception('can not find channel')
        logging.debug(f'[{self.live_info.room_id}] '
                      f'live channel: {self.live_info.parent_area}-{self.live_info.child_area} -> '
                      f'{self.video_info.channel[0]}-{self.video_info.channel[1]}')

    @staticmethod
    def set_pages(videos: list[str]) -> list[video_uploader.VideoUploaderPage]:
        """ 分页设置

        :param videos: 视频列表
        :return: 分页
        """
        pages = []
        index = 1
        for video in videos:
            # make sure the video exists and size is not 0
            if os.path.exists(video) and os.path.getsize(video) > 0:
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
        """ 获取分区id

        :param parent_area: 父区域
        :param child_area: 子区域
        :return: 分区id
        """
        channel = FileUtils.ReadJson(path=channel_data)
        tid = 0
        for main_ch in channel:
            if main_ch['name'] == parent_area:
                for sub_ch in main_ch['sub']:
                    if sub_ch['name'] == child_area:
                        tid = sub_ch['tid']
        return tid

    async def upload(self) -> bool:
        """ 上传视频

        :return: 是否上传成功
        """
        delete_flag = False
        success = False
        self.video_info.title = self.set_module(module_string=self.video_info.title)
        self.video_info.description = self.set_module(module_string=self.video_info.description)
        self.video_info.dynamic = self.set_module(module_string=self.video_info.dynamic)
        try:
            self.set_tags_and_channel()
            logging.info(f'[{self.live_info.room_id}] fetching channel...')
            tid = self.fetch_channel(parent_area=self.video_info.channel[0], child_area=self.video_info.channel[1])
            meta = {
                'act_reserve_create': 0,
                'copyright': 2,
                'source': 'https://live.bilibili.com/%d' % self.room_id,
                'desc': self.video_info.description,
                'dynamic': self.video_info.dynamic,
                'interactive': 0,
                'no_reprint': 0,
                'open_elec': 0,
                'origin_state': 0,
                'subtitles': {
                    "lan": '',
                    'open': 0
                    },
                'tag': self.video_info.get_tags(),
                'tid': tid,
                'title': self.video_info.title,
                'up_close_danmaku': False,
                'up_close_reply': False,
                'up_selection_reply': False
            }
            pages = self.set_pages(videos=self.videos)
            if len(pages) == 0:
                delete_flag = True
                raise FileNotFoundError('no videos to upload')
            uploader = video_uploader.VideoUploader(pages=pages, meta=meta, credential=self.credential)
            logging.info('uploading...')
            logging.debug('file info:\ntitle: %s\ntid: %d\ntags: %s' %
                          (self.video_info.title, tid, self.video_info.get_tags()))
            ids = await uploader.start()
            logging.info('uploading finished, bvid=%s, aid=%s' % (ids['bvid'], ids['aid']))
            success = True
        except Exception as e:
            logging.error(e)
        finally:
            return success or delete_flag
