import asyncio
from datetime import datetime
import logging
import os

import requests
from bilibili_api import Credential
from sanic import Sanic
from utils.BilibiliUploader import Uploader
from utils.VideoProcessor import Processor
from utils.FileUtils import DeleteFolder, DeleteFiles
from entity import RoomConfig, GlobalConfig, LiveInfo

app = Sanic.get_app()


@app.signal('session.start.<room_id:int>')
def session_start(room_id: int) -> None:
    """ 直播会话开始

    :param room_id: 房间id
    :return:
    """
    start_time = datetime.now()
    logging.debug(f'[{room_id}] live session started at {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    Processor.live_start(room_id=room_id, start_time=start_time)


@app.signal('file.open.<room_id:int>')
def file_open(room_id: int, file_path: str) -> None:
    """ 录播文件写入

    :param room_id: 房间id
    :param file_path: 录播文件路径
    :return:
    """
    logging.debug(f'[{room_id}] file path: {file_path}')
    Processor.file_open(room_id=room_id, file_path=file_path)


@app.signal('session.end.<room_id:int>')
async def session_end(room_id: int, event_data: dict, room_config: RoomConfig) -> None:
    """ 直播会话结束

    :param room_id: 房间id
    :param event_data: 录播姬webhook发送的event_data
    :param room_config: 房间配置
    :return:
    """
    global_config: GlobalConfig = app.ctx.global_config
    process = Processor(event_data=event_data, room_config=room_config)
    process.live_end()
    # check if the room need to be processed
    if process.check_if_need_process():
        logging.info(f'[{room_id}] processing...')
        try:
            await process.prepare(multipart=global_config.multipart)
        except FileExistsError as e:
            logging.warning(e)
            return
        logging.info(f'[{room_id}] mixing damaku into videos...')
        result_videos = await process.composite()
        logging.info(f'[{room_id}] successfully proceed videos')
        # send webhook
        for url in global_config.webhooks:
            app.add_task(send_webhook(
                url=url, event_data=event_data, videos=result_videos,
                work_dir=os.path.join(global_config.process_dir, process.live_info.session_id)
            ))
        # add video to upload queue
        if not global_config.auto_upload:
            logging.info(f'[{room_id}] adding videos to waiting list...')
        upload_queue = app.ctx.upload_queue
        upload_queue.put({
            'videos': result_videos,
            'origin_videos': process.origin_videos,
            'live_info': process.live_info
        })
        if global_config.auto_upload:
            logging.info(f'[{room_id}] uploading videos...')
            requests.get(f'http://localhost:{global_config.port}/video-upload')
    else:
        # not need to process + delete_flag -> delete files
        if global_config.delete_flag:
            logging.info(f'[{room_id}] deleting origin videos by global config...')
            DeleteFiles(files=process.origin_videos, types=['flv', 'xml'])


@app.signal('record.upload.<room_id:int>')
async def video_upload(room_id: int, room_config: RoomConfig, credential: Credential, video_info: dict) -> None:
    """ 上传视频

    :param room_id: 房间id
    :param room_config: 房间配置
    :param video_info: 视频信息
    :param credential: 用户凭证
    :return:
    """
    global_config = app.ctx.global_config
    uploader = Uploader(credential=credential, room_config=room_config, **video_info)
    result = await uploader.upload()
    if result:
        # successfully upload or no proper files -> delete files
        live_info: LiveInfo = video_info['live_info']
        dir_path = os.path.join(global_config.process_dir, live_info.session_id)
        logging.info(f'[{room_id}] deleting proceed videos in folder {dir_path}...')
        DeleteFolder(dir_path)
        if global_config.delete_flag:
            logging.info(f'[{room_id}] deleting origin videos by global config...')
            DeleteFiles(files=video_info.get('origin_videos'), types=['flv', 'xml'])
    else:
        # failed upload -> add to upload queue again
        logging.warning(f'[{room_id}] failed upload videos, adding to upload queue again...')
        upload_queue = app.ctx.upload_queue
        upload_queue.put(video_info)


async def send_webhook(url: str, event_data: dict, videos: list[str], work_dir: str):
    logging.info(f'send webhook to {url}')
    request_body = {
        'EventType': 'VideoProceed',
        'TimeStamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'EventData': event_data,
        'ProceedVideos': videos,
        'WorkDictionary': work_dir
    }
    headers = {
        'User-Agent': 'Record Uploader',
        'content-type': 'application/json'
    }
    # send webhook to url with requests and set timeout 100s (retry 3 times)
    for _ in range(3):
        with requests.post(url, json=request_body, headers=headers, timeout=100) as response:
            if response.status_code == 200:
                logging.info(f'send webhook to {url} successfully')
                return
            else:
                logging.error(f'{response.status_code}: {response.reason}')
