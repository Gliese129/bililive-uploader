import datetime
import logging
import os
import queue
import threading
import asyncio
from utils.BilibiliUploader import Uploader
from utils.VideoProcessor import Processor
from utils.FileUtils import DeleteFolder, DeleteFiles
from WebhookThread import WebhookThread
from config import RoomConfig, GlobalConfig


def session_start(room_id: int):
    """
    直播开始
    """
    start_time = datetime.datetime.now()
    logging.debug('room: %d  live start at %s' % (room_id, start_time.strftime('%Y-%m-%d %H:%M:%S')))
    Processor.live_start(room_id=room_id, start_time=start_time)


def file_open(room_id: int, event_data: dict):
    file_path = event_data['RelativePath']
    logging.debug('room: %d  file: %s' % (room_id, file_path))
    Processor.file_open(room_id=room_id, file_path=file_path)


async def session_end(upload_queue: queue.Queue, json_request: dict, global_config: GlobalConfig,
                      room_config: RoomConfig, room_id: int):
    process = Processor(event_data=json_request['EventData'], global_config=global_config)
    process.live_end()
    if process.check_if_need_process(configs=room_config.rooms):  # 需要处理上传
        logging.info('processing...')
        process.prepare()
        logging.info('converting danmaku files...')
        await process.make_damaku()
        logging.info('mixing damaku into videos...')
        result_videos = await process.composite()
        logging.info('successfully proceed videos!')
        webhook = WebhookThread(name='WebhookThread', webhooks=global_config.webhooks,
                                event_data=json_request['EventData'], proceed_videos=result_videos,
                                work_dic=os.path.join(global_config.process_dir, process.session_id))
        webhook.run()
        logging.info('adding videos to upload waiting list...')
        upload_queue.put({
            'room_config': process.config,
            'videos': result_videos,
            'parent_area': process.parent_area,
            'child_area': process.child_area,
            'start_time': process.start_time,
            'live_title': process.title,
            'room_id': room_id,
            'session_id': process.session_id,
            'origin_videos': process.origin_videos
        })


def video_upload(global_config: GlobalConfig, video_info: dict, access_key: dict):
    uploader = Uploader(access_key=access_key, **video_info)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(uploader.upload())
    dir_path = os.path.join(global_config.process_dir, video_info.get('session_id'))
    logging.info('deleting proceed videos in folder %s...' % dir_path)
    DeleteFolder(dir_path)
    if global_config.delete_flag:
        logging.info('deleting origin videos by global config...')
        DeleteFiles(files=video_info.get('origin_videos'), types=['flv', 'xml'])
    loop.close()


class ProcessThread (threading.Thread):
    event_type: str
    data: dict
    upload_queue: queue.Queue

    def __init__(self, upload_queue: queue.Queue, name: str = None, event_type: str = None, data: dict = None):
        threading.Thread.__init__(self, name=name)
        if data is None:
            data = {}
        self.event_type = event_type
        self.data = data
        self.upload_queue = upload_queue

    def run(self) -> None:
        logging.info('starting thread: %s...' % self.event_type)
        if self.event_type == 'SessionStarted':
            logging.info('received webhook: session started')
            session_start(**self.data)
        elif self.event_type == 'FileOpening':
            logging.info('received webhook: file opening')
            file_open(**self.data)
        elif self.event_type == 'SessionEnded':
            logging.info('received webhook: session ended')
            loop = asyncio.get_event_loop()
            loop.run_until_complete(session_end(upload_queue=self.upload_queue, **self.data))
        logging.info('thread: %s ended' % self.event_type)

