import asyncio
import logging
import os
from datetime import datetime

import requests
from sanic import Sanic

from entity import RoomConfig, BotConfig
from utils import FileUtils
from .handler import Process
from ..process import bp

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')


@bp.signal('session.start.<room_id:int>')
def session_start(room_id: int, start_time: datetime):
    """record session start time"""
    logger.info('Recording session started at %s',
                start_time.isoformat(), extra={'room_id': room_id})
    rooms = FileUtils.readJson(app.config.TIME_CACHE_PATH)
    rooms[str(room_id)] = start_time.isoformat()
    FileUtils.writeDict(app.config.TIME_CACHE_PATH, rooms)


@bp.signal('file.open.<room_id:int>')
def file_open(room_id: int, file_path: str):
    """record livestream file name"""
    logger.debug('Writing record data to "%s"...', file_path, extra={'room_id': room_id})
    relative_folder, name = os.path.split(file_path)
    folder = os.path.join(app.ctx.bot_config.rec_dir, relative_folder)  # relative -> absolute
    name = os.path.splitext(name)[0]
    extensions = ['.flv', '.xml'] if app.ctx.bot_config.danmaku else ['.flv']
    for extension in extensions:  # check if file exists
        if not os.path.exists(os.path.join(folder, name + extension)):
            logger.warning('%s should exist in %s, but not found',
                           name + extension, folder)

    rooms = FileUtils.readJson(app.config.VIDEO_CACHE_PATH)
    if str(room_id) not in rooms:
        rooms[str(room_id)] = {
            'folder': folder,
            'filenames': [],
            'extensions': extensions
        }
    rooms[str(room_id)]['filenames'].append(name)
    FileUtils.writeDict(app.config.VIDEO_CACHE_PATH, rooms)


@bp.signal('session.end.<room_id:int>')
async def session_end(room_id: int, event_data: dict, room_config: RoomConfig):
    """ 录制结束
    开始处理录播

    :param room_id
    :param event_data
    :param room_config
    :return:
    """
    logger.info('Recording session ended.', extra={'room_id': room_id})
    processor = Process(event_data, room_config)
    processor.live_end()
    if processor.need_process:
        logger.info('Processing...', extra={'room_id': room_id})
        bp.ctx.process_pool.sumbit(asyncio.run, _process, args=(processor, event_data, room_id))
    else:
        logger.info('No need to process.', extra={'room_id': room_id})


async def _process(processor: Process, event_data: dict, room_id: int):
    await processor.process()
    # webhook
    loop = asyncio.get_event_loop()
    tasks = []
    for url in app.ctx.bot_config.webhooks:
        tasks += loop.create_task(send_webhook(url, event_data, processor.processes))
    loop.run_until_complete(tasks)
    # upload
    videos = [os.path.join(processor.process_dir, item) + '.flv' for item in processor.processes]
    if app.ctx.bot_config.auto_upload:
        body = {
            'origins': processor.origins,
            'videos': videos,
            'live_info': processor.live_info,
            'folder': processor.process_dir
        }
        requests.post(f'http://localhost:{app.ctx.bot_config.port}/upload', json=body, timeout=100)
        logger.debug('Upload process triggered.', extra={'room_id': room_id})


async def send_webhook(url: str, event_data: dict, videos: list[str]):
    logger.info('Sending webhook to %s...', url)
    bot_config: BotConfig = app.ctx.bot_config
    body = {
        'EventType': 'ProcessFinished',
        'TimeStamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'BililiveData': event_data,
        'ProceedVideos': [video.replace(bot_config.work_dir, '') for video in videos],
        'WorkDirectory': bot_config.work_dir
    }
    headers = {
        'User-Agent': 'Bililive Uploader',
        'content-type': 'application/json'
    }
    for _ in range(3):
        with requests.post(url, json=body, headers=headers, timeout=100) as response:
            if response.status_code == 200:
                logger.debug('Webhook sent.')
                return
            logger.warning('Webhook sent failed. Status code: %d', response.status_code)
            await asyncio.sleep(0.5)
    logger.error('Webhook sent failed. Status code: %d', response.status_code)
