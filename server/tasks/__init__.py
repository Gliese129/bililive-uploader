import asyncio
import logging
import os
from datetime import datetime

import requests
from bilibili_api import Credential
from sanic import Sanic

from entity import BotConfig, RoomConfig, LiveInfo
from exceptions import ChannelNotFoundException, UploadVideosNotFoundException
from utils import FileUtils
from .process import Process
from .upload import Upload

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')


@app.signal('session.start.<room_id:int>')
def session_start(room_id: int, start_time: datetime):
    """ 录制开始
    记录直播开始时间

    :param room_id
    :param start_time:
    :return:
    """
    logger.info('Recording session started at %s', start_time.isoformat(), extra={'room_id': room_id})
    Process.session_start(room_id, start_time)


@app.signal('file.open.<room_id:int>')
def file_open(room_id: int, file_path: str):
    """ 录播文件写入
    记录录播文件路径

    :param room_id
    :param file_path
    :return:
    """
    logger.debug('Writing record data to "%s"...', file_path, extra={'room_id': room_id})
    Process.file_open(room_id, file_path)


@app.signal('session.end.<room_id:int>')
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
        await processor.process()
        # webhook
        [asyncio.create_task(send_webhook(url, event_data, processor.processes)) for url in app.ctx.bot_config.webhooks]
        # upload
        videos = [os.path.join(processor.process_dir, item) + '.flv' for item in processor.processes]
        app.ctx.upload_queue.put({
            'origins': processor.origins,
            'videos': videos,
            'live_info': processor.live_info,
            'folder': processor.process_dir
        })
        logger.info('Added videos to upload queue.', extra={'room_id': room_id})
        if app.ctx.bot_config.auto_upload:
            requests.get(f'http://localhost:{app.ctx.bot_config.port}/upload')
    else:
        logger.info('No need to process.', extra={'room_id': room_id})


@app.signal('record.upload.<room_id:int>')
async def start_upload(room_id: int, room_config: RoomConfig, credential: Credential, info: dict):
    """ 开始上传
    从上传队列中取出视频并上传

    :param room_id
    :param room_config
    :param credential
    :param info: {videos, live_info, folder}
    :return:
    """
    bot_config: BotConfig = app.ctx.bot_config
    uploader = Upload(room_config=room_config, credential=credential, **info)
    origins = info['origins']
    folder = info['folder']
    try:
        await uploader.upload()
        logger.info('Uploaded successfully.', extra={'room_id': room_id})
        FileUtils.deleteFolder(folder)
        if bot_config.delete:
            files = [origin + extension for origin in origins for extension in ('.flv', '.xml')]
            FileUtils.deleteFiles(files)
    except (ChannelNotFoundException, UploadVideosNotFoundException) as e:
        logger.error('Uploading failed.', extra={'room_id': room_id})
        app.ctx.upload_queue.put(info)


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
                logger.info('Webhook sent.')
                return
            logger.warning('Webhook sent failed. Status code: %d', response.status_code)
            await asyncio.sleep(1)
    logger.error('Webhook sent failed. Status code: %d', response.status_code)
