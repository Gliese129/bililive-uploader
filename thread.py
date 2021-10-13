import datetime
import logging
import threading
from utils.BilibiliUploader import Uploader
from utils.VideoProcessor import Processor
from config import RoomConfig, GlobalConfig


def session_start(room_id: int):
    start_time = datetime.datetime.now()
    logging.debug('room: %d  live start at %s' % (room_id, start_time.strftime('%Y-%m-%d %H:%M:%S')))
    Processor.live_start(room_id=room_id, start_time=start_time)


def file_open(room_id: int, event_data: dict):
    file_path = event_data['RelativePath']
    logging.debug('room: %d  file: %s' % (room_id, file_path))
    Processor.file_open(room_id=room_id, file_path=file_path)


async def session_end(json_request: dict, global_config: GlobalConfig, room_config: RoomConfig, room_id: int):
    process = Processor(event_data=json_request['EventData'], global_config=global_config)
    process.live_end()
    if process.check_if_need_process(configs=room_config.rooms):  # 需要处理上传
        logging.info('processing...')
        process.prepare()
        logging.info('converting danmaku files...')
        await process.make_damaku()
        logging.info('mixing damaku into videos...')
        result_videos = await process.composite()
        logging.info('successfully proceed videos, now starting to upload...')
        uploader = Uploader(global_config=global_config, room_config=process.config, videos=result_videos,
                            parent_area=process.parent_area, child_area=process.child_area,
                            start_time=process.start_time, live_title=process.title,
                            room_id=room_id)
        await uploader.upload()


class ProcessThread (threading.Thread):
    event_type: str
    data: dict

    def __init__(self, name: str = None, event_type: str = None, data: dict = None):
        threading.Thread.__init__(self, name=name)
        if data is None:
            data = {}
        self.event_type = event_type
        self.data = data

    def run(self):
        if self.event_type == 'SessionStarted':
            logging.info('received webhook: session started')
            session_start(**self.data)
        elif self.event_type == 'FileOpening':
            logging.info('received webhook: file opening')
            file_open(**self.data)
        elif self.event_type == 'SessionEnded':
            logging.info('received webhook: session ended')
            session_end(**self.data)
