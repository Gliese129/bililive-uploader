# -*- coding: utf-8 -*-
import logging
from bilibili_api import video_uploader
from utils import FileUtils
from config import Room, LiveInfo, VideoInfo
from utils.FileUtils import ReadJson

channel_data = './resources/channel.json'
live_to_video_data = './resources/live-to-video.json'


class Uploader:
    credential: video_uploader.Credential
    videos: list[str]
    room_id: int
    live_info: LiveInfo
    video_info: VideoInfo
    room_config: Room
    channel: (str, str)

    def __init__(self, access_key: dict, room_config: Room, videos: list[str], live_info: LiveInfo):
        self.credential = video_uploader.Credential(**access_key)
        self.videos = videos
        self.video_info = VideoInfo(room_config=room_config)
        self.live_info = live_info
        self.room_id = live_info.room_id

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
        # 现在room_config中设置channel和tags
        self.room_config.channel = self.room_config.channel
        self.room_config.tags = self.room_config.tags
        # 在live-to-video中查找channel，查到则直接替换
        live_to_video = ReadJson(path=live_to_video_data)
        for parent_area in live_to_video:
            flag = False
            if parent_area.get('name') == self.live_info.parent_area:
                # 直播父分区可以直接对应频道
                if parent_area.get('channel') is not None:
                    channel = Room.get_channel(parent_area.get('channel'))
                    if channel is not None:
                        self.channel = channel
                        flag = True
                # 直播父分区无法直接对应，查找子分区
                elif parent_area.get('children') is not None:
                    for child_area in parent_area.get('children'):
                        if child_area.get('name') == self.live_info.child_area:
                            # 子分区可以直接对应频道
                            if child_area.get('channel') is not None:
                                channel = Room.get_channel(child_area.get('channel'))
                                if channel is not None:
                                    self.channel = channel
                                    flag = True
                                    break
                if flag:
                    break
        # 最后在condition中查找channel，追加tags
        conditions = self.room_config.list_proper_conditions(live_info=self.live_info)
        for condition in conditions:
            self.video_info.tags.extend(condition.tags)
            self.channel = condition.channel

    @staticmethod
    def set_pages(videos: list[str]) -> list[video_uploader.VideoUploaderPage]:
        """ 分页设置

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
        """ 获取分区id

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

    async def upload(self) -> bool:
        """ 上传视频

        :return: 是否上传成功
        """
        success = False
        self.video_info.title = self.set_module(module_string=self.video_info.title)
        self.video_info.description = self.set_module(module_string=self.video_info.description)
        self.video_info.dynamic = self.set_module(module_string=self.video_info.dynamic)
        try:
            tid = self.fetch_channel(parent_area=self.channel[0], child_area=self.channel[1])
            meta = {
                'copyright': 2,  # 投稿类型 1-自制，2-转载
                'source': 'https://live.bilibili.com/%d' % self.room_id,  # 视频来源。投稿类型为转载时注明来源，为原创时为空
                'desc': self.video_info.description,  # 视频简介
                'dynamic': self.video_info.dynamic,  # 视频动态
                'desc_format_id': 0,
                'open_elec': 0,  # 是否展示充电信息  1-是，0-否
                'no_reprint': 0,  # 显示未经作者授权禁止转载，仅当为原创视频时有效  1-启用，0-关闭
                'subtitles': {
                    "lan": '',  # 字幕投稿语言，不清楚作用请将该项设置为空
                    'open': 1  # 是否启用字幕投稿，1 or 0
                    },
                'interactive': 0,
                'tag': self.video_info.get_tags(),  # 视频标签。使用英文半角逗号分隔的标签组。示例：标签1,标签2,标签3
                'tid': tid,  # 分区ID。可以使用 channel 模块进行查询
                'title': self.video_info.title,  # 视频标题
                'up_close_danmaku': False,  # 是否关闭弹幕
                'up_close_reply': False,  # 是否关闭评论
            }
            pages = self.set_pages(videos=self.videos)
            for page in pages:
                uploader = video_uploader.VideoUploader(pages=[page], meta=meta, credential=self.credential)
                logging.info('uploading...')
                logging.debug('file info:\ntitle: %s\ntid: %d\ntags: %s' %
                              (self.video_info.title, tid, self.video_info.tags))
                ids = await uploader.start()
                logging.info('uploading finished, bvid=%s, aid=%s' % (ids['bvid'], ids['aid']))
            success = True
        except Exception as e:
            logging.error(e)
        finally:
            return success
