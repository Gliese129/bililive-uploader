from datetime import datetime
import logging
import os
import queue
import threading
import asyncio
from utils.BilibiliUploader import Uploader
from utils.VideoProcessor import Processor
from utils.FileUtils import DeleteFolder, DeleteFiles
from WebhookThread import WebhookThread
from config import RoomConfig, GlobalConfig, LiveInfo


def session_start(room_id: int) -> None:
    """ 直播会话开始

    :param room_id: 房间id
    :return:
    """
    start_time = datetime.now()
    logging.debug(f'room: {room_id}  live start at {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    Processor.live_start(room_id=room_id, start_time=start_time)


def file_open(room_id: int, file_path: str) -> None:
    """ 录播文件写入

    :param room_id: 房间id
    :param file_path: 录播文件路径
    :return:
    """
    logging.debug(f'room: {room_id}  file: {file_path}')
    Processor.file_open(room_id=room_id, file_path=file_path)


async def session_end(event_data: dict, global_config: GlobalConfig, room_config: RoomConfig,
                      room_id: int, upload_queue: queue.Queue) -> None:
    """ 直播会话结束

    :param event_data: 录播姬webhook发送的event_data
    :param global_config: 全局配置
    :param room_config: 房间配置
    :param room_id: 房间id
    :param upload_queue: 上传队列
    :return:
    """
    process = Processor(event_data=event_data, global_config=global_config)
    process.live_end()
    # check if the room need to be processed
    if process.check_if_need_process(configs=room_config):
        logging.info('processing...')
        process.prepare()
        logging.info('converting danmaku files...')
        await process.make_damaku()
        logging.info('mixing damaku into videos...')
        result_videos = await process.composite()
        logging.info('successfully proceed videos')
        # starting webhook thread
        webhook = WebhookThread(name=f'Webhook room {room_id}', webhooks=global_config.webhooks,
                                event_data=event_data, proceed_videos=result_videos,
                                work_dic=os.path.join(global_config.process_dir, process.live_info.session_id))
        webhook.run()
        # add video to upload queue
        logging.info('adding videos to upload waiting list...')
        upload_queue.put({
            'room_config': process.config,
            'videos': result_videos,
            'origin_videos': process.origin_videos,
            'live_info': process.live_info
        })


async def video_upload(global_config: GlobalConfig, access_key: dict, video_info: dict,
                       upload_queue: queue.Queue) -> None:
    """ 上传视频

    :param global_config: 全局配置
    :param video_info: 视频信息
    :param access_key: 密钥
    :param upload_queue: 上传视频队列
    :return:
    """
    uploader = Uploader(access_key=access_key, **video_info)
    result = await uploader.upload()
    if result:
        # successfully upload -> delete files
        dir_path = os.path.join(global_config.process_dir, video_info.get('session_id'))
        logging.info(f'deleting proceed videos in folder {dir_path}...')
        DeleteFolder(dir_path)
        if global_config.delete_flag:
            logging.info('deleting origin videos by global config...')
            DeleteFiles(files=video_info.get('origin_videos'), types=['flv', 'xml'])
    else:
        # failed upload -> add to upload queue again
        upload_queue.put(video_info)


class ProcessThread (threading.Thread):
    """ 处理线程

    Fields:
        event_type: webhook事件类型
        data: 传输的数据
        upload_queue: 上传视频队列
    """
    event_type: str
    data: dict
    upload_queue: queue.Queue

    def __init__(self, upload_queue: queue.Queue, name: str = None, event_type: str = None, data: dict = None):
        threading.Thread.__init__(self, name=name)
        self.event_type = event_type
        self.data = {} if data is None else data
        self.upload_queue = upload_queue

    def run(self) -> None:
        logging.info(f'starting thread: {self.name}...')
        asyncio.set_event_loop(asyncio.new_event_loop())
        if self.event_type == 'SessionStarted':
            logging.info('received webhook: session started')
            session_start(**self.data)
        elif self.event_type == 'FileOpening':
            logging.info('received webhook: file opening')
            file_open(**self.data)
        elif self.event_type == 'SessionEnded':
            logging.info('received webhook: session ended')
            asyncio.run(session_end(upload_queue=self.upload_queue, **self.data))
        elif self.event_type == 'FileUploading':
            logging.info('received request: upload')
            asyncio.run(video_upload(upload_queue=self.upload_queue, **self.data))
