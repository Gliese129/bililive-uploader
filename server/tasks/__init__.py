import logging
from datetime import datetime

from sanic import Sanic

from entity import BotConfig, RoomConfig
from .process import Process

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
def session_end(room_id: int, event_data: dict, room_config: RoomConfig):
    """ 录制结束
    开始处理录播

    :param room_id
    :param event_data
    :param room_config
    :return:
    """
    logger.info('Recording session ended.', extra={'room_id': room_id})
    bot_config: BotConfig = app.ctx.bot_config
    processor = Process(event_data, room_config)
    processor.live_end()
    if processor.need_process:
        logger.info('Processing...', extra={'room_id': room_id})

    else:
        logger.info('No need to process.', extra={'room_id': room_id})
