from datetime import datetime
import logging
import os
from sanic import Sanic
from utils.BilibiliUploader import Uploader
from utils.VideoProcessor import Processor
from utils.FileUtils import DeleteFolder, DeleteFiles
from config import RoomConfig, GlobalConfig, LiveInfo

app = Sanic.get_app()


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


async def session_end(event_data: dict, global_config: GlobalConfig, room_config: RoomConfig) -> None:
    """ 直播会话结束

    :param event_data: 录播姬webhook发送的event_data
    :param global_config: 全局配置
    :param room_config: 房间配置
    :return:
    """
    process = Processor(event_data=event_data, global_config=global_config)
    process.live_end()
    # check if the room need to be processed
    if process.check_if_need_process(configs=room_config):
        logging.info('processing...')
        try:
            process.prepare()
        except FileExistsError as e:
            logging.warning(e)
            return
        logging.info('converting danmaku files...')
        await process.make_damaku()
        logging.info('mixing damaku into videos...')
        result_videos = await process.composite()
        logging.info('successfully proceed videos')
        # starting webhook thread
        for url in global_config.webhooks:
            app.add_task(dispatch_task(f'custom.webhook-send.{url}', data={
                'event_data': event_data,
                'proceed_videos': result_videos,
                'work_dic': os.path.join(global_config.process_dir, process.live_info.session_id)
            }))
        # add video to upload queue
        logging.info('adding videos to upload waiting list...')
        upload_queue = app.ctx.upload_queue
        upload_queue.put({
            'room_config': process.config,
            'videos': result_videos,
            'origin_videos': process.origin_videos,
            'live_info': process.live_info
        })
    else:
        # not need to process + delete_flag -> delete files
        if global_config.delete_flag:
            logging.info('deleting origin videos by global config...')
            DeleteFiles(files=process.origin_videos, types=['flv', 'xml'])


async def video_upload(global_config: GlobalConfig, access_key: dict, video_info: dict) -> None:
    """ 上传视频

    :param global_config: 全局配置
    :param video_info: 视频信息
    :param access_key: 密钥
    :return:
    """
    uploader = Uploader(access_key=access_key, **video_info)
    result = await uploader.upload()
    if result:
        # successfully upload or no proper files -> delete files
        live_info: LiveInfo = video_info['live_info']
        dir_path = os.path.join(global_config.process_dir, live_info.session_id)
        logging.info(f'deleting proceed videos in folder {dir_path}...')
        DeleteFolder(dir_path)
        if global_config.delete_flag:
            logging.info('deleting origin videos by global config...')
            DeleteFiles(files=video_info.get('origin_videos'), types=['flv', 'xml'])
    else:
        # failed upload -> add to upload queue again
        upload_queue = app.ctx.upload_queue
        upload_queue.put(video_info)


async def send_webhook(url: str, event_data: dict, videos: list[str], work_dir: str):
    logging.info(f'Send webhook to {url}')
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
    # send webhook to url with sanic and set timeout 100s (retry 3 times)
    async with app.test_client() as client:
        for i in range(3):
            flag = False
            try:
                async with client.post(url, json=request_body, headers=headers, timeout=100) as response:
                    if response.status == 200:
                        logging.info(f'Send webhook to {url} success')
                        flag = True
                    else:
                        logging.error(f'{response.status}: {response.reason}')
                        raise Exception(f'{response.status}: {response.reason}')
            finally:
                if flag:
                    break


async def dispatch_task(taskname: str, data: dict):
    """ 分发任务

    :param taskname: 任务名称
    :param data: 任务数据
    :return:
    """
    if taskname == 'session-start':
        session_start(**data)
    elif taskname == 'file-open':
        file_open(**data)
    elif taskname == 'session-end':
        await session_end(**data)
    elif taskname == 'video-upload':
        await video_upload(**data)
    elif taskname == 'send-webhook':
        await send_webhook(**data)