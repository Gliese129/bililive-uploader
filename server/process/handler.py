import logging
import os

from sanic import Sanic

from entity import LiveInfo, RoomConfig
from exceptions import UnknownError
from utils import FileUtils, VideoUtils

from .utils import merge_videos, merge_danmaku, convert_danmakus, combine_videos_and_danmakus

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')

TRANSFORMED_NAME = 'record'
PROCESSED_PREFIX = 'result'


class Process:
    """ This class is responsible for processing videos.

    It takes event data and room configuration as input,
    and provides methods for merging, making danmaku, and combining videos.


    Attributes:
        folder: 录播文件所属文件夹
        origins: 原始文件名（不带后缀）
        process_dir: 处理后文件所在文件夹
        processes: 处理文件名（不带后缀）
        extensions: 后缀名
        live_info: 直播信息
        room_config: 房间配置
    """
    folder: str
    origins: list[str]
    process_dir: str
    processes: list[str]
    extensions: list[str]
    live_info: LiveInfo
    room_config: RoomConfig

    def __init__(self, event_data: dict, room_config: RoomConfig):
        self.live_info = LiveInfo(event_data)
        self.origins, self.processes = [], []
        self.room_config = room_config
        self.live_info.read_start_time(app.config.TIME_CACHE_PATH, self.live_info.room_id)

    def live_end(self):
        rooms = FileUtils.readJson(app.config.VIDEO_CACHE_PATH)
        if str(self.live_info.room_id) not in rooms:
            raise UnknownError(f'Room {self.live_info.room_id} not found in video_cache.json')
        room = rooms.pop(str(self.live_info.room_id))
        FileUtils.writeDict(app.config.VIDEO_CACHE_PATH, rooms)
        self.folder, self.origins, self.extensions = room['folder'], room['filenames'], room['extensions']
        self.generate_process_dir()

    def generate_process_dir(self):
        room_id = self.live_info.room_id
        start_time = self.live_info.start_time
        bot_config = app.ctx.bot_config
        self.process_dir = os.path.join(bot_config.work_dir, f'{room_id}_{start_time.strftime("%Y%m%d-%H%M%S")}')

    @property
    def need_process(self) -> bool:
        # whether this room is in config
        if self.room_config is None:
            logger.debug('Room not found in config.', extra={'room_id': self.live_info.room_id})
            return False
        # whether videos exist
        if len(self.origins) == 0:
            logger.warning('No video found.', extra={'room_id': self.live_info.room_id})
            return False
        # whether this room is filtered by extra config
        for condition in self.room_config.list_conditions(self.live_info):
            if not condition.process:
                logger.debug('Room filtered by extra conditions, '
                             'details: item -- %s | regexp -- %s',
                             condition.item, condition.regexp, extra={'room_id': self.live_info.room_id})
                return False
        # whether total time is enough
        videos = [os.path.join(self.folder, origin + '.flv') for origin in self.origins]
        total_time = VideoUtils.getTotalTime(videos)
        if total_time < app.ctx.bot_config.min_time:
            logger.debug('Total time is not enough, details: total time -- %s | min time -- %s',
                         total_time, app.ctx.bot_config.min_time, extra={'room_id': self.live_info.room_id})
            return False
        return True

    async def process(self):
        # move files to process_dir
        assert not os.path.exists(self.process_dir), UnknownError(f"Process dir '{self.process_dir}' shouldn't exist.")
        os.makedirs(self.process_dir)
        logger.info('Moving files to process dir.', extra={'room_id': self.live_info.room_id})
        files = [os.path.join(self.folder, origin + extension)
                 for origin in self.origins for extension in self.extensions]
        # move and rename files
        moved = FileUtils.copyFiles(files, self.process_dir)
        news = [os.path.join(self.process_dir, TRANSFORMED_NAME + str(i) + extension)
                for i in range(len(self.origins)) for extension in self.extensions]
        FileUtils.renameFiles(list(zip(moved, news)))
        self.processes = [TRANSFORMED_NAME + str(i) for i in range(len(self.origins))]
        # process videos
        if not app.ctx.bot_config.multipart and len(self.processes) > 1:
            await self.merge()
        await self.make_danmaku()
        await self.combine()

    async def merge(self):
        """ Merge seperated danmaku xml files and flv files to 1 file each. """
        logger.info('Merging files...', extra={'room_id': self.live_info.room_id})
        videos = [os.path.join(self.process_dir, process + '.flv') for process in self.processes]
        danmakus = [os.path.join(self.process_dir, process + '.xml') for process in self.processes]
        # videos
        await merge_videos(videos, self.process_dir, TRANSFORMED_NAME + '.flv')
        FileUtils.deleteFiles(videos)
        # danmakus
        await merge_danmaku(danmakus, self.process_dir, TRANSFORMED_NAME + '.xml')
        FileUtils.deleteFiles(danmakus)
        self.processes = [TRANSFORMED_NAME]

    async def make_danmaku(self):
        xml_files = [os.path.join(self.process_dir, process + '.xml') for process in self.processes]
        ass_files = [os.path.join(self.process_dir, process + '.ass') for process in self.processes]
        logger.debug('Transforming damaku files:\ninputs: %s\noutputs: %s',
                     xml_files, ass_files, extra={'room_id': self.live_info.room_id})
        await convert_danmakus(list(zip(xml_files, ass_files)))

    async def combine(self):
        logger.info('Combining record videos and danmaku...', extra={'room_id': self.live_info.room_id})
        videos = [os.path.join(self.process_dir, process + '.flv') for process in self.processes]
        danmakus = [os.path.join(self.process_dir, process + '.ass') for process in self.processes]
        outputs = [os.path.join(self.process_dir, f'{PROCESSED_PREFIX}{i}.flv') for i in range(len(self.processes))]
        logger.debug('Combining videos:\ninput videos: %s\ninput danmakus: %s\noutput: %s',
                     videos, danmakus, outputs, extra={'room_id': self.live_info.room_id})
        await combine_videos_and_danmakus(list(zip(videos, danmakus, outputs)))
        self.processes = [PROCESSED_PREFIX + str(i) for i in range(len(self.processes))]
        FileUtils.deleteFiles(videos)
        FileUtils.deleteFiles(danmakus)
