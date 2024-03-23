import asyncio
import logging
import queue
import threading
import time

import schedule
from sanic import Sanic, text, Blueprint

from entity import RoomConfig, LiveInfo, BotConfig

logger = logging.getLogger('bililive-uploader')
bp = Blueprint('upload', url_prefix='/upload')
UPLOAD_LOCK = threading.Lock()


@bp.route('/')
async def add_upload_video(request):
    """add video to upload queue"""
    data = request.json
    if not data:
        return text('No data received.')
    app = Sanic.get_app()
    app.ctx.upload_queue.put(data)
    logger.info('Received video to upload.', extra={'room_id': data['live_info'].room_id})
    logger.debug('Details:\n %s', data)
    _upload_videos(app.ctx.upload_queue, app.ctx.bot_config)
    return text('Received.')


@bp.route('/start')
async def upload_video(_):
    """trigger upload process manually"""
    app = Sanic.get_app()
    _upload_videos(app.ctx.upload_queue, app.ctx.bot_config)
    return text('Start uploading...')


def init_upload_thread(app: Sanic):
    """this function will start a new thread to upload videos every day at 06:00"""

    def upload_schedule(app: Sanic):
        schedule.every().day.at('06:00').do(_upload_videos,
                                            app.ctx.upload_queue, app.ctx.bot_config)
        schedule.run_all()
        while True:
            schedule.run_pending()
            time.sleep(1)

    # start a new thread to upload videos
    upload_thread = threading.Thread(target=upload_schedule, args=(app,))
    upload_thread.start()


def _upload_videos(upload_queue: queue.Queue, bot_config: BotConfig):
    with UPLOAD_LOCK:
        upload_list = []
        while not upload_queue.empty():
            upload_list.append(upload_queue.get())
        logger.info('Got %d videos to upload.', len(upload_list))
        logger.debug('Details:\n %s', upload_list)

        loop = asyncio.new_event_loop()
        upload_tasks = [_dispatch(f'record.upload.{item["live_info"].room_id}',
                                  credential=bot_config.credential,
                                  info=item,
                                  room_config=RoomConfig.init(bot_config.work_dir,
                                                              item['live_info'].room_id,
                                                              item['live_info'].short_id)
                                  ) for item in upload_list]
        loop.run_until_complete(asyncio.wait(upload_tasks))
        loop.close()


async def _dispatch(route: str, **kwargs):
    await bp.dispatch(route, context=kwargs)
