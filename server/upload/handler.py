import logging
import os

from bilibili_api import Credential
from bilibili_api.video_uploader import VideoUploaderPage, VideoUploader
from sanic import Sanic

from entity import LiveInfo, UploadInfo, RoomConfig, BotConfig
from exceptions import ChannelNotFoundException, UploadVideosNotFoundException
from utils import FileUtils

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')

VIDEO_CHANNEL_PATH = './resources/channel.json'
LIVE2VIDEO_MAP_PATH = 'live2video.json'


class Upload:
    """ upload videos

    Attributes:
        credential: B站凭据
        live_info: 直播信息
        upload_info: 上传信息
        room_config: 房间配置
    """
    credential: Credential
    live_info: LiveInfo
    upload_info: UploadInfo
    room_config: RoomConfig

    def __init__(self, credential: Credential, room_config: RoomConfig,
                 live_info: LiveInfo, videos: list[str], **_):
        self.credential = credential
        self.live_info = live_info
        self.upload_info = UploadInfo(room_config, videos)
        self.room_config = room_config

    @staticmethod
    def get_tid_by_channel(parent_area: str, child_area: str) -> int:
        """ get channel tid from channel.json

        :exception ChannelNotFoundException
        """
        channel = FileUtils.readJson(VIDEO_CHANNEL_PATH)
        for main in channel:
            if main['name'] == parent_area:
                for sub in main['sub']:
                    if sub['name'] == child_area:
                        return sub['tid']
        raise ChannelNotFoundException('Cannot find channel in channel.json.',
                                       parent_area, child_area)

    def set_tags_and_channel(self):
        """ set tags and video channel tid

        :exception ChannelNotFoundException
        """
        bot_config: BotConfig = app.ctx.bot_config
        # from room config
        self.upload_info.channel = self.room_config.channel
        self.upload_info.tags = self.room_config.tags

        # from live2video.json
        def find_channel() -> (str, str):
            live2video = FileUtils.readJson(bot_config.path2absolute(os.path.join('resources', LIVE2VIDEO_MAP_PATH)))
            for parent_area in live2video:
                if parent_area.get('name') == self.live_info.parent_area:
                    if parent_area.get('channel'):
                        return parent_area['channel']
                    if parent_area.get('sub'):
                        for child_area in parent_area['sub']:
                            if child_area.get('name') == self.live_info.child_area:
                                return child_area['channel']
            return None

        result = find_channel()
        if result:
            self.upload_info.channel = result

        # from extra conditions
        conditions = self.room_config.list_conditions(self.live_info)
        for condition in conditions:
            self.upload_info.tags.extend(condition.tags)
            if condition.channel:
                self.upload_info.channel = condition.channel

        # if no channel found, throw exception
        if not self.upload_info.channel:
            raise ChannelNotFoundException('Cannot find channel in live2video.json.',
                                           self.live_info.parent_area, self.live_info.child_area)
        logger.debug('live channel: %s-%s  -->  video channel: %s-%s',
                     self.live_info.parent_area, self.live_info.child_area,
                     self.upload_info.channel[0], self.upload_info.channel[1],
                     extra={'room_id': self.live_info.room_id})

    @staticmethod
    def set_pages(videos: list[str]) -> list[VideoUploaderPage]:
        """ set pages for multi videos """
        pages = []
        for i, video in enumerate(videos):
            if os.path.exists(video) and os.path.getsize(video) > 0:
                info = {
                    'path': video,
                    'title': f'part{i + 1}',
                    'description': '',
                }
                page = VideoUploaderPage(**info)
                pages.append(page)
        return pages

    async def upload(self):
        """ upload videos to bilibili

        :exception ChannelNotFound
        :exception VideosNotFound
        :return:
        """
        self.upload_info.title = self.live_info.fill_module_string(self.upload_info.title)
        self.upload_info.description = self.live_info.fill_module_string(self.upload_info.description)
        self.set_tags_and_channel()
        tid = self.get_tid_by_channel(*self.upload_info.channel)
        meta = {
            'act_reserve_create': 0,
            'copyright': 2,  # 转载
            'source': f'https://live.bilibili.com/{self.live_info.room_id}',  # 直播间
            'desc': self.upload_info.description,
            'dynamic': self.upload_info.dynamic,
            'interactive': 0,
            'no_reprint': 0,
            'open_elec': 0,
            'origin_state': 0,
            'subtitles': {
                "lan": '',
                'open': 0
            },
            'tag': self.upload_info.tags_str,
            'tid': tid,
            'title': self.upload_info.title,
            'up_close_danmaku': False,
            'up_close_reply': False,
            'up_selection_reply': False
        }
        logger.debug('upload info: \n%s', meta, extra={'room_id': self.live_info.room_id})
        pages = self.set_pages(self.upload_info.videos)
        if len(pages) == 0:
            raise UploadVideosNotFoundException('Cannot find videos to upload.')
        uploader = VideoUploader(pages=pages, meta=meta, credential=self.credential)
        logger.info('Uploading videos...', extra={'room_id': self.live_info.room_id})
        ids = await uploader.start()
        logger.info('Upload videos success. bvid=%s, aid=%s', ids['bvid'], ids['aid'],
                    extra={'room_id': self.live_info.room_id})
